from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import threading
import time
import uuid
import urllib.request
from dataclasses import asdict, dataclass, field, fields
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .audit import AuditLedger, LocalRoutePolicy, RouteCandidate


SCHEMA = "hal.open_local_node.v0"
DEFAULT_CONFIG = Path.home() / ".hal-open-local-ai" / "node.json"


class NodeConfigError(ValueError):
    pass


@dataclass(frozen=True)
class NodeConfig:
    model: str = "qwen2.5:3b"
    ollama_url: str = "http://127.0.0.1:11434"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8844
    audit_path: str = str(Path.home() / ".hal-open-local-ai" / "audit.jsonl")
    audit_key: str = field(default_factory=lambda: secrets.token_hex(32))
    timeout_s: float = 120.0
    max_request_bytes: int = 1_000_000
    max_response_bytes: int = 2_000_000

    def validate(self) -> "NodeConfig":
        if not self.model.strip():
            raise NodeConfigError("model is required")
        if self.bind_host != "127.0.0.1":
            raise NodeConfigError("HAL Node v0 binds only to 127.0.0.1")
        if not 1 <= int(self.bind_port) <= 65535:
            raise NodeConfigError("bind_port must be 1..65535")
        if len(self.audit_key) < 32:
            raise NodeConfigError("audit_key must contain at least 32 characters")
        if self.timeout_s <= 0:
            raise NodeConfigError("timeout_s must be positive")
        if not 1_024 <= int(self.max_request_bytes) <= 10_000_000:
            raise NodeConfigError("max_request_bytes outside bounded range")
        if not 1_024 <= int(self.max_response_bytes) <= 10_000_000:
            raise NodeConfigError("max_response_bytes outside bounded range")

        decision = LocalRoutePolicy().choose([
            RouteCandidate(
                route_id="ollama",
                endpoint=self.ollama_url,
                data_residency="local",
                model=self.model,
            )
        ])
        if not decision.allowed:
            raise NodeConfigError("ollama_url must be explicit loopback HTTP")

        parsed = urlsplit(self.ollama_url)
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise NodeConfigError(
                "ollama_url must be the loopback origin only, without path/query/fragment"
            )
        return self

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "NodeConfig":
        allowed = {item.name for item in fields(cls)}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise NodeConfigError(f"unknown config keys: {', '.join(unknown)}")
        if "audit_key" not in payload:
            raise NodeConfigError(
                "audit_key is required in persisted config; rerun init-config"
            )
        return cls(**dict(payload)).validate()


def load_config(path: Path) -> NodeConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NodeConfigError(f"config not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise NodeConfigError(f"config is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise NodeConfigError("config must be a JSON object")
    return NodeConfig.from_mapping(payload)


def write_config(path: Path, config: NodeConfig, *, force: bool = False) -> Path:
    config.validate()
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing config: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(asdict(config), indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


class LocalNodeRuntime:
    def __init__(self, config: NodeConfig):
        self.config = config.validate()
        self.ledger = AuditLedger(self.config.audit_path)
        damaged_index = self.ledger.verify()
        if damaged_index is not None:
            raise RuntimeError(
                f"audit ledger integrity check failed at record {damaged_index}"
            )
        self._audit_lock = threading.Lock()

    def _keyed_digest(self, value: bytes) -> str:
        return hmac.new(
            self.config.audit_key.encode("utf-8"),
            value,
            hashlib.sha256,
        ).hexdigest()

    def _audit(self, event_type: str, payload: dict[str, Any]) -> str:
        with self._audit_lock:
            records = self.ledger.read()
            previous = records[-1].get("event_hash", "") if records else ""
            return self.ledger.append(event_type, payload, previous_hash=previous)

    @staticmethod
    def _validate_messages(messages: Any) -> list[dict[str, str]]:
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list")
        normalized: list[dict[str, str]] = []
        total = 0
        for item in messages:
            if not isinstance(item, dict):
                raise ValueError("each message must be an object")
            role = str(item.get("role", ""))
            content = item.get("content")
            if role not in {"system", "user", "assistant"} or not isinstance(
                content, str
            ):
                raise ValueError(
                    "messages require system/user/assistant role and text content"
                )
            total += len(content.encode("utf-8"))
            if total > 500_000:
                raise ValueError("message content exceeds local node limit")
            normalized.append({"role": role, "content": content})
        return normalized

    def _request_ollama(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.config.ollama_url.rstrip("/") + "/api/chat",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "hal-open-local-node/0",
            },
            method="POST",
        )
        with urllib.request.urlopen(
            request,
            timeout=self.config.timeout_s,
        ) as response:
            raw = response.read(self.config.max_response_bytes + 1)
        if len(raw) > self.config.max_response_bytes:
            raise RuntimeError("Ollama response exceeded configured limit")
        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise RuntimeError("Ollama response must be a JSON object")
        return decoded

    def ollama_ready(self) -> bool:
        request = urllib.request.Request(
            self.config.ollama_url.rstrip("/") + "/api/tags",
            headers={"User-Agent": "hal-open-local-node/0"},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=min(5.0, self.config.timeout_s),
            ) as response:
                payload = json.loads(
                    response.read(1_000_000).decode("utf-8")
                )
            models = payload.get("models") if isinstance(payload, dict) else None
            if not isinstance(models, list):
                return False
            available = {
                str(item.get("name") or item.get("model") or "")
                for item in models
                if isinstance(item, dict)
            }
            return self.config.model in available
        except Exception:
            return False

    def chat(self, messages: Any) -> dict[str, Any]:
        normalized = self._validate_messages(messages)
        canonical = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        request_id = uuid.uuid4().hex
        prompt_digest = self._keyed_digest(canonical)
        started = time.perf_counter()
        self._audit(
            "chat_requested",
            {
                "request_id": request_id,
                "model": self.config.model,
                "message_count": len(normalized),
                "roles": [message["role"] for message in normalized],
                "prompt_hmac_sha256": prompt_digest,
                "route": "loopback_ollama",
            },
        )
        try:
            payload = self._request_ollama({
                "model": self.config.model,
                "messages": normalized,
                "stream": False,
            })
            message = payload.get("message")
            content = (
                message.get("content")
                if isinstance(message, dict)
                else None
            )
            if not isinstance(content, str):
                raise RuntimeError(
                    "Ollama response did not contain assistant text"
                )
            response_digest = self._keyed_digest(content.encode("utf-8"))
            elapsed_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )
            self._audit(
                "chat_completed",
                {
                    "request_id": request_id,
                    "model": self.config.model,
                    "response_hmac_sha256": response_digest,
                    "latency_ms": elapsed_ms,
                    "prompt_eval_count": int(
                        payload.get("prompt_eval_count") or 0
                    ),
                    "eval_count": int(payload.get("eval_count") or 0),
                },
            )
            prompt_tokens = int(payload.get("prompt_eval_count") or 0)
            completion_tokens = int(payload.get("eval_count") or 0)
            return {
                "id": f"hal-local-{request_id}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": self.config.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
            }
        except Exception as exc:
            self._audit(
                "chat_failed",
                {
                    "request_id": request_id,
                    "model": self.config.model,
                    "error_type": type(exc).__name__,
                    "latency_ms": round(
                        (time.perf_counter() - started) * 1000,
                        2,
                    ),
                },
            )
            raise


def build_server(runtime: LocalNodeRuntime) -> ThreadingHTTPServer:
    allowed_hosts = {
        f"127.0.0.1:{runtime.config.bind_port}",
        f"localhost:{runtime.config.bind_port}",
    }
    allowed_origins = {
        f"http://127.0.0.1:{runtime.config.bind_port}",
        f"http://localhost:{runtime.config.bind_port}",
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "HALOpenLocalNode/0"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _json(
            self,
            status: int,
            payload: dict[str, Any],
        ) -> None:
            body = json.dumps(
                payload,
                separators=(",", ":"),
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.end_headers()
            self.wfile.write(body)

        def _same_origin_request(self) -> bool:
            if self.client_address[0] != "127.0.0.1":
                return False

            host = (self.headers.get("Host") or "").strip().lower()
            if host not in allowed_hosts:
                return False

            origin = (self.headers.get("Origin") or "").strip().lower()
            if origin and origin not in allowed_origins:
                return False

            referer = (self.headers.get("Referer") or "").strip()
            if referer and not origin:
                parsed = urlsplit(referer)
                referer_origin = (
                    f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
                )
                if referer_origin not in allowed_origins:
                    return False

            fetch_site = (
                self.headers.get("Sec-Fetch-Site") or ""
            ).strip().lower()
            if fetch_site and fetch_site not in {"same-origin", "none"}:
                return False
            return True

        def _authorize_local_request(self) -> bool:
            if self._same_origin_request():
                return True
            self._json(403, {"error": "local_origin_required"})
            return False

        def do_GET(self) -> None:
            if not self._authorize_local_request():
                return
            if self.path == "/health":
                self._json(200, {
                    "schema": SCHEMA,
                    "status": "ok",
                    "service": "hal-open-local-node",
                    "local_only": True,
                    "model": runtime.config.model,
                })
                return
            if self.path == "/ready":
                ready = runtime.ollama_ready()
                self._json(
                    200 if ready else 503,
                    {
                        "schema": SCHEMA,
                        "status": (
                            "ready" if ready else "not_ready"
                        ),
                        "ollama": ready,
                        "model": runtime.config.model,
                    },
                )
                return
            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if not self._authorize_local_request():
                return
            if self.path != "/v1/chat/completions":
                self._json(404, {"error": "not_found"})
                return
            try:
                length = int(
                    self.headers.get("Content-Length") or "0"
                )
            except ValueError:
                length = 0
            if (
                length <= 0
                or length > runtime.config.max_request_bytes
            ):
                self._json(
                    413,
                    {"error": "invalid_or_oversized_body"},
                )
                return
            try:
                payload = json.loads(
                    self.rfile.read(length).decode("utf-8")
                )
                if not isinstance(payload, dict):
                    raise ValueError("body must be an object")
                if payload.get("stream") not in (None, False):
                    raise ValueError(
                        "streaming is not supported in HAL Node v0"
                    )
                requested_model = payload.get("model")
                if requested_model not in (
                    None,
                    runtime.config.model,
                ):
                    raise ValueError(
                        "requested model is not the configured local model"
                    )
                result = runtime.chat(payload.get("messages"))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._json(
                    502,
                    {
                        "error": "local_ollama_unavailable",
                        "detail": type(exc).__name__,
                    },
                )
                return
            self._json(200, result)

    return ThreadingHTTPServer(
        (runtime.config.bind_host, runtime.config.bind_port),
        Handler,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HAL Open Local AI node v0"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser(
        "init-config",
        help="write a local-only node configuration",
    )
    init.add_argument("--model", default="qwen2.5:3b")
    init.add_argument("--port", type=int, default=8844)
    init.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
    )
    init.add_argument("--force", action="store_true")

    sub.add_parser(
        "doctor",
        help="validate config and local Ollama readiness",
    )
    sub.add_parser(
        "serve",
        help="serve the loopback-only chat gateway",
    )

    args = parser.parse_args(argv)
    if args.command == "init-config":
        config = NodeConfig(
            model=args.model,
            bind_port=args.port,
            ollama_url=args.ollama_url,
            audit_path=str(args.config.parent / "audit.jsonl"),
        ).validate()
        write_config(
            args.config,
            config,
            force=args.force,
        )
        print(args.config)
        return 0

    config = load_config(args.config)
    runtime = LocalNodeRuntime(config)
    if args.command == "doctor":
        report = {
            "schema": SCHEMA,
            "config_valid": True,
            "local_only": True,
            "ollama_ready": runtime.ollama_ready(),
            "model": config.model,
            "bind": (
                f"http://{config.bind_host}:{config.bind_port}"
            ),
        }
        print(json.dumps(report, indent=2))
        return 0 if report["ollama_ready"] else 2

    server = build_server(runtime)
    print(
        f"HAL Open Local Node v0 listening on "
        f"http://{config.bind_host}:{config.bind_port}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
