"""Local read-only web GUI for repair-005 progress artifacts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from experiments.monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005 import (
    DEFAULT_LOG_ROOT,
    build_status,
)

INDEX_PATH = Path(__file__).with_name("rts_gmlc_repair_005_gui") / "index.html"


class AttemptNotFoundError(ValueError):
    """The requested attempt is not an enumerated log directory."""


def _warning(message: str) -> dict[str, str]:
    return {"message": message}


def list_attempts(log_root: Path) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    root = Path(log_root)
    if not root.is_dir():
        return [], [_warning("日志目录不存在或不可访问")]
    try:
        children = list(root.iterdir())
    except OSError as error:
        return [], [_warning(f"无法读取日志目录: {error}")]
    attempts: list[dict[str, object]] = []
    warnings: list[dict[str, str]] = []
    for child in children:
        try:
            progress = child / "progress.jsonl"
            if not child.is_dir() or not progress.is_file():
                continue
            modified = progress.stat().st_mtime
        except OSError as error:
            warnings.append(_warning(f"无法检查 attempt {child.name}: {error}"))
            continue
        attempts.append(
            {
                "id": child.name,
                "modified_utc": datetime.fromtimestamp(
                    modified, tz=timezone.utc
                ).isoformat(),
            }
        )
    attempts.sort(key=lambda item: str(item["modified_utc"]), reverse=True)
    return attempts, warnings


def _select_attempt(
    log_root: Path, attempt_id: str | None
) -> tuple[Path | None, list[dict[str, object]], list[dict[str, str]]]:
    attempts, warnings = list_attempts(log_root)
    if not attempts:
        if attempt_id:
            raise AttemptNotFoundError("attempt 不存在")
        return None, attempts, warnings
    known = {str(item["id"]) for item in attempts}
    selected = attempt_id or str(attempts[0]["id"])
    if selected not in known:
        raise AttemptNotFoundError("attempt 不存在")
    return Path(log_root) / selected, attempts, warnings


def _read_events(path: Path, limit: int = 40) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        return [], [_warning(f"无法读取进度事件: {error}")]
    events: list[dict[str, object]] = []
    malformed = 0
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(row, Mapping) or row.get("event") == "heartbeat":
            continue
        if not isinstance(row.get("event"), str):
            malformed += 1
            continue
        events.append(
            {
                "event": row["event"],
                "timestamp_utc": row.get("timestamp_utc"),
                "elapsed_seconds": row.get("monotonic_elapsed_seconds"),
                "candidate": row.get("requested_candidate_id")
                or row.get("candidate_id"),
                "candidate_ordinal": row.get("candidate_ordinal"),
                "stage": row.get("stage"),
                "iteration": row.get("iteration"),
                "solve_label": row.get("solve_label") or row.get("call_id"),
                "initial_strategy": row.get("initial_strategy"),
                "error_type": row.get("error_type"),
                "error_message": row.get("error_message"),
            }
        )
    warnings = [_warning(f"忽略了 {malformed} 条不完整事件")] if malformed else []
    return events[-limit:], warnings


def _read_log_tail(
    value: object, attempt_root: Path, line_limit: int = 120
) -> tuple[dict[str, object], list[dict[str, str]]]:
    empty = {"relative_path": None, "text": "", "truncated": False}
    if not isinstance(value, str) or not value:
        return empty, []
    try:
        root = attempt_root.resolve(strict=True)
        path = Path(value).resolve(strict=True)
        relative = path.relative_to(root)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, ValueError) as error:
        return empty, [_warning(f"当前 solver 日志不可读取: {error}")]
    return {
        "relative_path": str(relative),
        "text": "\n".join(lines[-line_limit:]),
        "truncated": len(lines) > line_limit,
    }, []


def _make_handler(log_root: Path) -> type[BaseHTTPRequestHandler]:
    """Return a handler class bound to *log_root*."""

    class _Handler(BaseHTTPRequestHandler):
        def _send_json(self, data: object, *, status: int = 200) -> None:
            body = (
                json.dumps(data, allow_nan=False, ensure_ascii=False) + "\n"
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path, content_type: str) -> None:
            try:
                body = path.read_bytes()
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlsplit(self.path)
            route = parsed.path.rstrip("/") or "/"
            params = {k: v[0] for k, v in parse_qs(parsed.query).items() if v}

            if route in ("/", "/index.html"):
                self._send_file(INDEX_PATH, "text/html; charset=utf-8")
                return

            if route == "/api/attempts":
                attempts, warnings = list_attempts(log_root)
                self._send_json({"attempts": attempts, "warnings": warnings})
                return

            if route == "/api/status":
                attempt_id = params.get("attempt")
                try:
                    attempt_path, attempts, warnings = _select_attempt(
                        log_root, attempt_id
                    )
                except AttemptNotFoundError as exc:
                    self._send_json({"error": str(exc)}, status=404)
                    return
                if attempt_path is None:
                    self._send_json(
                        {"status": "missing", "warnings": warnings, "attempts": attempts}
                    )
                    return
                status = build_status(attempt_path)
                self._send_json({**status, "attempts": attempts})
                return

            if route == "/api/events":
                attempt_id = params.get("attempt")
                limit = max(1, min(200, int(params.get("limit", "60"))))
                try:
                    attempt_path, _, _ = _select_attempt(log_root, attempt_id)
                except AttemptNotFoundError as exc:
                    self._send_json({"error": str(exc)}, status=404)
                    return
                if attempt_path is None:
                    self._send_json({"events": [], "warnings": ["尚无 attempt 日志"]})
                    return
                events, warnings = _read_events(
                    attempt_path / "progress.jsonl", limit=limit
                )
                self._send_json({"events": events, "warnings": warnings})
                return

            if route == "/api/log":
                attempt_id = params.get("attempt")
                native_log = params.get("log", "")
                try:
                    attempt_path, _, _ = _select_attempt(log_root, attempt_id)
                except AttemptNotFoundError as exc:
                    self._send_json({"error": str(exc)}, status=404)
                    return
                if attempt_path is None:
                    self._send_json({"error": "尚无 attempt 日志"}, status=404)
                    return
                log_data, warnings = _read_log_tail(native_log, attempt_path)
                self._send_json({"log": log_data, "warnings": warnings})
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, *_args: object) -> None:  # suppress access log
            pass

    return _Handler


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-root",
        type=Path,
        default=Path(
            "results/logs/"
            "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_005"
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8705)
    args = parser.parse_args(argv)
    log_root = Path(args.log_root)
    handler = _make_handler(log_root)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"repair-005 GUI → {url}  (Ctrl-C 停止)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
