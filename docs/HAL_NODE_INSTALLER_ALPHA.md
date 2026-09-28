# HAL Node installer alpha

This repository contains a bounded first step toward a non-expert local AI node.

## What it does

`scripts/install_hal_node.ps1`:
- checks that Python and Ollama are already present;
- displays the exact local-only endpoint and model;
- supports a dry run;
- writes one user-local `node.json` plan through the dependency-free Python planner.

The plan is accepted only when its route is explicit loopback HTTP. The default is `http://127.0.0.1:11434`.

## What it deliberately does not do

The alpha does **not**:
- download or install Python/Ollama;
- start or modify a Windows service;
- pull a model;
- read or store credentials;
- open firewall ports;
- contact a cloud model or remote peer;
- change HAL SUPREME;
- claim that a peer mesh exists.

This keeps the first installer slice auditable and reversible. The next installer milestone is an owner-reviewed prerequisite acquisition flow plus a real second-machine canary.

## Dry run

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install_hal_node.ps1 -DryRun
```

## Write the plan

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install_hal_node.ps1 -Model qwen2.5:3b
```

Or use Python directly:

```text
python tools/plan_node.py --model qwen2.5:3b --output node.json
```

The resulting plan is data, not execution authority.
