import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from hal_public_interest.node import (
    LocalNodeRuntime,
    NodeConfig,
    NodeConfigError,
    build_server,
)


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": [{"name": "qwen2.5:3b"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return
        size = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(size))
        assert payload["stream"] is False
        body = json.dumps({
            "message": {"role": "assistant", "content": "local answer"},
            "prompt_eval_count": 4,
            "eval_count": 2,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def fake_ollama():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def config(tmp_path, fake_ollama, port=8844):
    return NodeConfig(
        model="qwen2.5:3b",
        ollama_url=fake_ollama,
        bind_port=port,
        audit_path=str(tmp_path / "audit.jsonl"),
    ).validate()


def test_config_refuses_remote_or_non_loopback_routes(tmp_path):
    for endpoint in [
        "https://api.example.com",
        "http://192.168.1.9:11434",
        "http://127.0.0.1.evil.example:11434",
    ]:
        with pytest.raises(NodeConfigError):
            NodeConfig(
                ollama_url=endpoint,
                audit_path=str(tmp_path / "a.jsonl"),
            ).validate()


def test_runtime_calls_only_local_ollama_and_audits_hashes_not_prompt(
    tmp_path, fake_ollama
):
    runtime = LocalNodeRuntime(config(tmp_path, fake_ollama))
    result = runtime.chat([{"role": "user", "content": "PRIVATE PROMPT"}])
    assert result["choices"][0]["message"]["content"] == "local answer"
    assert result["usage"]["total_tokens"] == 6
    records = runtime.ledger.read()
    serialized = json.dumps(records)
    assert "PRIVATE PROMPT" not in serialized
    assert "prompt_sha256" in serialized
    assert [r["event_type"] for r in records] == [
        "chat_requested",
        "chat_completed",
    ]
    assert runtime.ledger.verify() is None


def test_ready_proves_local_ollama_reachable(tmp_path, fake_ollama):
    runtime = LocalNodeRuntime(config(tmp_path, fake_ollama))
    assert runtime.ollama_ready() is True


def test_openai_shaped_loopback_endpoint(tmp_path, fake_ollama):
    port = _free_port()
    runtime = LocalNodeRuntime(config(tmp_path, fake_ollama, port=port))
    server = build_server(runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps({
            "model": "qwen2.5:3b",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        }).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read())
        assert payload["object"] == "chat.completion"
        assert payload["choices"][0]["message"]["content"] == "local answer"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_gateway_rejects_wrong_model_and_streaming(tmp_path, fake_ollama):
    port = _free_port()
    runtime = LocalNodeRuntime(config(tmp_path, fake_ollama, port=port))
    server = build_server(runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        bodies = [
            {
                "model": "other",
                "messages": [{"role": "user", "content": "x"}],
            },
            {
                "model": "qwen2.5:3b",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ]
        for body in bodies:
            data = json.dumps(body).encode()
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(request, timeout=3)
            assert exc.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
