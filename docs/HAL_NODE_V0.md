# HAL Node v0 alpha

HAL Node v0 is a bounded local-compute prototype built from the public-interest
repository's existing local-route policy and hash-linked audit ledger.

It is intentionally smaller than HAL SUPREME. It provides one thing:

- a loopback-only OpenAI-shaped chat endpoint backed by a local Ollama model.

There is no cloud fallback, credential store, peer mesh, remote access,
autonomous tool use, billing, public listener, or HAL SUPREME private state.

## Security boundary

The node accepts an Ollama upstream only when `LocalRoutePolicy` proves that
the configured endpoint is explicit loopback HTTP.

V0 itself binds only to `127.0.0.1`.

The audit ledger stores:

- request ID;
- model;
- message count and roles;
- SHA-256 of canonicalized messages;
- response SHA-256;
- token counts and latency;
- failure type when a local call fails.

It does **not** store prompt or response text.

## Requirements

- Python 3.11 or newer.
- Windows 10 or later for the bootstrap script.
- Ollama for the real local model runtime.

Ollama's current official Windows download page publishes a PowerShell installer
at `https://ollama.com/install.ps1`, and its Windows runtime serves a local API
on `http://localhost:11434`. HAL's bootstrap uses the exact HTTPS installer
URL only when `-InstallOllama` is explicitly supplied.

## Review before applying

The bootstrap defaults to plan mode:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_hal_node_windows.ps1
```

That command does not install Ollama or pull a model.

To install the local package and create the configuration when Ollama already
exists:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_hal_node_windows.ps1 -Apply
```

Optional network-changing steps are separate switches:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_hal_node_windows.ps1 -Apply -InstallOllama -PullModel
```

`-InstallOllama` downloads Ollama's official Windows installer script to a
temporary file, records its SHA-256, executes it, then deletes the temporary
copy. It does not pipe network content directly to `iex`.

`-PullModel` downloads the configured Ollama model. V0 defaults to
`qwen2.5:3b`; that default is a prototype choice, not a claim that it is the
best model for every machine.

## Manual configuration

```bash
python -m pip install .
hal-open-node --config ~/.hal-open-local-ai/node.json init-config --model qwen2.5:3b
hal-open-node --config ~/.hal-open-local-ai/node.json doctor
hal-open-node --config ~/.hal-open-local-ai/node.json serve
```

On Windows the generated config is under the user's home directory at
`.hal-open-local-ai/node.json`.

The endpoint is:

```text
http://127.0.0.1:8844/v1/chat/completions
```

Health and readiness:

```text
GET /health
GET /ready
```

`/health` is node liveness. `/ready` checks the local Ollama API.

## Example local request

```powershell
$body = @{
  model = "qwen2.5:3b"
  stream = $false
  messages = @(@{ role = "user"; content = "Explain local AI in one sentence." })
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8844/v1/chat/completions -ContentType "application/json" -Body $body
```

## What remains before calling this an easy-to-deploy node

This pull request is an alpha and does not prove non-expert deployment.

Required next evidence:

1. Windows CI passes on the exact branch.
2. Run the bootstrap on a second physical Windows machine.
3. Record time-to-ready, hardware, Ollama version, model download size, failures,
   user interventions, and hashes.
4. Have a second person follow the instructions without developer coaching.
5. Add uninstall/recovery behavior based on what the pilot exposes.
6. Only then tighten the one-command path.

Peer routing and community mesh behavior are separate future milestones and must
not be claimed from this alpha.
