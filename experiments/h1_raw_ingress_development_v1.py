"""One-owner raw-before-consumer adapter, development only; no native runner.

Producer/consumer are explicit callbacks. Their return never certifies science.
Create once; inspection is read-only and never provides resume/retry authority.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import threading

SCHEMA = 'h1_raw_ingress_development_v1'
RAW_CAP = 16 * 1024 * 1024
META_CAP = 2048


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw): return sha256(raw).hexdigest()


def same(actual, expected): return encode(actual) == encode(expected)


def identity(path):
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('regular file required')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_stable(path, cap):
    before = identity(path)
    if before[2] > cap:
        raise ValueError('file byte cap exceeded')
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        opened = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        # Windows Python can expose birth-time via path stat's ctime but
        # change-time via fstat's ctime. Compare that field within each API.
        if opened[:4] != before[:4]:
            raise ValueError('file replaced before open')
        raw = stream.read(cap+1)
        info = os.fstat(stream.fileno())
        after = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if len(raw) > cap or len(raw) != before[2] or after != opened or identity(path) != before:
        raise ValueError('file changed or exceeded byte cap')
    return raw, before


def pin(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('SHA256 required')
    return value


def write_new(path, raw):
    with path.open('xb') as stream:
        if stream.write(raw) != len(raw):
            raise OSError('short write')
        stream.flush()
        os.fsync(stream.fileno())
    if read_stable(path, len(raw))[0] != raw:
        raise OSError('fresh readback mismatch')


def write_metadata(path, value):
    raw = encode(value)
    if len(raw) > META_CAP:
        raise ValueError('metadata cap exceeded')
    write_new(path, raw)
    return digest(raw)


class Ingress:
    def __init__(self, root, request_sha256, *, stages):
        pin(request_sha256)
        if type(stages) is not int or not 1 <= stages <= 232:
            raise ValueError('bounded stage count required')
        self.root = Path(root).resolve()
        self.request = request_sha256
        self.stages = stages
        self.next_stage = 0
        self.poisoned = False
        self.closed = False
        self.owner = (os.getpid(), threading.get_ident())
        self.root.mkdir(exist_ok=False)
        self.binding = dict(schema=SCHEMA, request_sha256=request_sha256,
                            stages=stages, raw_cap=RAW_CAP, meta_cap=META_CAP)
        self.head = write_metadata(self.root/'binding.json', self.binding)

    def _active(self):
        if self.owner != (os.getpid(), threading.get_ident()):
            raise ValueError('owner process/thread mismatch')
        if self.closed or self.poisoned:
            raise ValueError('closed or poisoned ingress')

    def deliver(self, index, producer, consumer):
        """Save every returned, in-cap raw before invoking consumer exactly once.

        Raw not returned by producer, over-cap output, or an interrupted write
        has no completeness guarantee. Such attempts are unknown; no retry.
        """
        self._active()
        if type(index) is not int or index != self.next_stage or index >= self.stages:
            self.poisoned = True
            raise ValueError('ordered unused stage required')
        stage = self.root/f'{index:03d}'
        try:
            stage.mkdir(exist_ok=False)
            intent = dict(schema=SCHEMA, stage=index, request_sha256=self.request,
                          previous=self.head)
            intent_sha = write_metadata(stage/'intent.json', intent)
            # A process stop from this point leaves intent without final outcome.
            raw = producer()
            if type(raw) is not bytes or not 0 < len(raw) <= RAW_CAP:
                raise ValueError('producer must return nonempty in-cap raw bytes')
            write_new(stage/'raw.bin', raw)
            receipt = dict(schema=SCHEMA, stage=index, intent_sha256=intent_sha,
                           raw_sha256=digest(raw), raw_bytes=len(raw))
            receipt_sha = write_metadata(stage/'raw_receipt.json', receipt)
            # Re-read from the durable ingress, not the producer's memory value.
            fresh = read_stable(stage/'raw.bin', RAW_CAP)[0]
            if len(fresh) != receipt['raw_bytes'] or digest(fresh) != receipt['raw_sha256']:
                raise OSError('raw changed before consumer')
            result = consumer(fresh)
            if read_stable(stage/'raw.bin', RAW_CAP)[0] != fresh:
                raise OSError('raw changed during consumer')
            self.head = write_metadata(stage/'outcome.json', dict(schema=SCHEMA,
                stage=index, raw_receipt_sha256=receipt_sha, state='consumer_returned'))
            self.next_stage += 1
            return result
        except BaseException:
            self.poisoned = True
            # Do not repair/overwrite an ambiguous write or fabricate an outcome.
            raise

    def abort(self):
        """Caller must propagate an error occurring after deliver returned."""
        self._active()
        self.poisoned = True
        write_metadata(self.root/'aborted.json', dict(schema=SCHEMA,
            request_sha256=self.request, next_stage=self.next_stage,
            last_outcome_sha256=self.head, state='external_consumer_failed'))

    def finish(self):
        self._active()
        if self.next_stage != self.stages:
            self.poisoned = True
            raise ValueError('incomplete stage sequence')
        try:
            write_metadata(self.root/'terminal.json', dict(schema=SCHEMA,
                stages=self.stages, last_outcome_sha256=self.head,
                request_sha256=self.request, state='callback_sequence_complete'))
            self.closed = True
            result = inspect(self.root, expected_request=self.request,
                             expected_binding_sha256=digest(encode(self.binding)))
            if not result['callback_sequence_complete']:
                raise ValueError('fresh inspection did not close')
            return result
        except BaseException:
            self.poisoned = True
            raise


def inspect(root, *, expected_request, expected_binding_sha256):
    """Fresh inspection: bounded files, exact chain, no repair and no execution."""
    pin(expected_request)
    pin(expected_binding_sha256)
    root = Path(root).resolve()
    result = dict(schema=SCHEMA, state='unresolved', retained_complete_raw=0,
                  consumer_returned=0, callback_sequence_complete=False,
                  errors=[], retry_authorized=False, native_execution_authenticated=False,
                  resource_admission=False, formal_result=False)
    observed = []
    listings = []

    def listing(path):
        names = {p.name for p in path.iterdir()}
        listings.append((path, names))
        return names

    def read_meta(path):
        raw, stamp = read_stable(path, META_CAP)
        observed.append((path, stamp))
        doc = json.loads(raw)
        if encode(doc) != raw:
            raise ValueError('noncanonical metadata')
        return doc, digest(raw)

    try:
        binding, head = read_meta(root/'binding.json')
        count = binding.get('stages')
        if (type(count) is not int or not 1 <= count <= 232 or
                not same(binding, dict(schema=SCHEMA, request_sha256=expected_request,
                    stages=count, raw_cap=RAW_CAP, meta_cap=META_CAP)) or head != expected_binding_sha256):
            raise ValueError('binding mismatch')
        allowed = {'binding.json', 'terminal.json', 'aborted.json'} | {f'{i:03d}' for i in range(count)}
        if listing(root) - allowed:
            raise ValueError('unexpected root entry')
        stopped = False
        for i in range(count):
            stage = root/f'{i:03d}'
            if not stage.exists():
                stopped = True
                continue
            if stopped:
                raise ValueError('stage after incomplete prefix')
            if not stage.is_dir() or listing(stage) - {'intent.json', 'raw.bin', 'raw_receipt.json', 'outcome.json'}:
                raise ValueError('unexpected stage entry')
            intent, intent_sha = read_meta(stage/'intent.json')
            if not same(intent, dict(schema=SCHEMA, stage=i, request_sha256=expected_request, previous=head)):
                raise ValueError('intent chain mismatch')
            if not (stage/'raw_receipt.json').exists():
                stopped = True
                continue
            receipt, receipt_sha = read_meta(stage/'raw_receipt.json')
            raw_path = stage/'raw.bin'
            raw, stamp = read_stable(raw_path, RAW_CAP)
            observed.append((raw_path, stamp))
            if not raw:
                raise ValueError('missing/oversize raw')
            if not same(receipt, dict(schema=SCHEMA, stage=i, intent_sha256=intent_sha,
                               raw_sha256=digest(raw), raw_bytes=len(raw))):
                raise ValueError('raw receipt mismatch')
            result['retained_complete_raw'] += 1
            if not (stage/'outcome.json').exists():
                stopped = True
                continue
            outcome, head = read_meta(stage/'outcome.json')
            if not same(outcome, dict(schema=SCHEMA, stage=i, raw_receipt_sha256=receipt_sha,
                               state='consumer_returned')):
                raise ValueError('outcome mismatch')
            result['consumer_returned'] += 1
        aborted = (root/'aborted.json').exists()
        if aborted:
            abort, _ = read_meta(root/'aborted.json')
            if not same(abort, dict(schema=SCHEMA, request_sha256=expected_request,
                next_stage=result['consumer_returned'], last_outcome_sha256=head,
                state='external_consumer_failed')):
                raise ValueError('abort mismatch')
            result['errors'].append('external_consumer_failed')
        if (root/'terminal.json').exists():
            terminal, _ = read_meta(root/'terminal.json')
            if aborted or stopped or not same(terminal, dict(schema=SCHEMA, stages=count, last_outcome_sha256=head,
                request_sha256=expected_request, state='callback_sequence_complete')):
                raise ValueError('terminal mismatch')
            result.update(state='callback_sequence_complete', callback_sequence_complete=True)
        else:
            result['errors'].append('terminal_missing')
        if any(identity(path) != stamp for path, stamp in observed):
            raise ValueError('inspection file view changed')
        if any({p.name for p in path.iterdir()} != names for path, names in listings):
            raise ValueError('inspection directory view changed')
    except (ValueError, OSError, TypeError, AttributeError) as error:
        # Bounded diagnostic code only; arbitrary exception text is not archived.
        result['errors'].append(type(error).__name__)
        result.update(state='unresolved', callback_sequence_complete=False)
    return result
