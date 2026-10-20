"""Fixed initial-episode execution/offline-audit entrypoint; needs an outer owner."""
import argparse
from hashlib import sha256
import os
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'src.rq2_joint_deliverability_boundary_v1'

from . import scale_episode_bidirectional_transport as transport, scale_episode_bidirectional_replay as replay

episode = transport.episode
controller = episode.controller
SCHEMA = 'draft_bidirectional_mixed_selector_episode_worker_v1'


def implementation_identity():
    return episode.tx.legacy._identity(SCHEMA, transport.implementation_identity(), replay.implementation_identity(),
                                      sha256(Path(__file__).read_bytes()).hexdigest())


def episode_environment(directory):
    directory = controller.local._path(directory)
    if not directory.is_dir(): raise ValueError('existing episode environment directory required')
    environment = dict(os.environ, TEMP=str(directory), TMP=str(directory))
    controller.process.process._environment_block(environment)
    return environment


def run_worker(*, mode, request_path, expected_request_sha256, max_request_bytes, episode_root,
               receipt_path, episode_environment_directory, expected_environment_sha256,
               expected_implementation_identity, header_sha256=None, intent_sha256s=(), result_sha256s=()):
    if mode not in ('execute', 'audit'): raise ValueError('fixed episode worker mode required')
    if mode == 'execute' and (header_sha256 is not None or intent_sha256s or result_sha256s):
        raise ValueError('execution cannot accept prefix/resume pins')
    if mode == 'audit':
        transport.selector.scale.actual._hash(header_sha256)
        if type(intent_sha256s) is not tuple or type(result_sha256s) is not tuple:
            raise ValueError('external ordered audit pins required')
    root, receipt = map(controller.local._path, (episode_root, receipt_path))
    if any(controller.local._path(path).is_relative_to(root)
           for path in (request_path, episode_environment_directory)):
        raise ValueError('episode inputs and environment must be outside evidence root')
    if receipt.is_relative_to(root) or not receipt.name.endswith('_non_authoritative.json') or receipt.exists():
        raise ValueError('new separate non_authoritative receipt required')
    environment = episode_environment(episode_environment_directory)
    def check():
        if implementation_identity() != expected_implementation_identity:
            raise ValueError('episode worker implementation drift')
        if sha256(controller.worker.store._bytes(episode_environment(episode_environment_directory))).hexdigest() != expected_environment_sha256:
            raise ValueError('episode worker environment mismatch')
        return transport.read_inputs(request_path, expected_sha256=expected_request_sha256, max_request_bytes=max_request_bytes)
    inputs = check()
    kwargs = dict(budget=inputs.budget, resource_plan=inputs.resource_plan, environment=environment)
    args = (root, inputs.reference_request, inputs.arms, inputs.hours)
    if mode == 'execute':
        with episode.DevelopmentBidirectionalEpisode(*args, **kwargs) as owner:
            for _ in inputs.hours: owner.advance()
            owner._check()
            pins = dict(header_sha256=owner._retained[root/'header.json'][1],
                intent_sha256s=tuple(owner._retained[root/f'{i:06d}.intent.json'][1] for i in range(len(inputs.hours))),
                result_sha256s=tuple(owner._retained[root/f'{i:06d}.result.json'][1] for i in range(len(inputs.hours))))
        outcome = dict(observation_window_consumed=True, completed_hours=len(inputs.hours), **pins)
    else:
        def forbidden(*args, **kwargs): raise RuntimeError('offline worker execution forbidden')
        targets = ((controller, 'supervise_selector'), (controller.process, 'normal_task_child'),
                   (episode.tx.scale.native, '_solve'))
        originals = [(obj, name, getattr(obj, name)) for obj, name in targets]
        try:
            for obj, name in targets: setattr(obj, name, forbidden)
            outcome = replay.audit_episode(*args, **kwargs, expected_header_sha256=header_sha256,
                expected_intent_sha256s=intent_sha256s, expected_result_sha256s=result_sha256s,
                expected_audit_identity=replay.implementation_identity())
        finally:
            for obj, name, original in originals: setattr(obj, name, original)
    check()
    result = dict(schema=SCHEMA, mode=mode, request_sha256=expected_request_sha256,
        implementation_identity=expected_implementation_identity, environment_sha256=expected_environment_sha256,
        episode_root=str(root), audit_pins=None if mode == 'execute' else dict(header_sha256=header_sha256,
            intent_sha256s=intent_sha256s, result_sha256s=result_sha256s),
        outcome=outcome, formal_result=False, whole_task_resources_verified=False,
        executable_resume_available=False)
    controller._write(receipt, result)
    check()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('execute', 'audit'), required=True)
    for name in ('request-path', 'expected-request-sha256', 'episode-root', 'receipt-path',
                 'episode-environment-directory', 'expected-environment-sha256', 'expected-implementation-identity'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--max-request-bytes', type=int, required=True)
    parser.add_argument('--header-sha256')
    parser.add_argument('--intent-sha256', action='append', default=[])
    parser.add_argument('--result-sha256', action='append', default=[])
    args = vars(parser.parse_args())
    args['intent_sha256s'] = tuple(args.pop('intent_sha256'))
    args['result_sha256s'] = tuple(args.pop('result_sha256'))
    run_worker(**args)


if __name__ == '__main__': main()
