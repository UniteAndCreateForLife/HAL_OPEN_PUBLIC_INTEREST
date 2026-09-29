# Sovereign Node Doctor - Foresight Local Compute prototype

This is an intentionally small first slice for the **Foresight AI for Science &
Safety Nodes - Local Compute** RFP.

The long-term proposal is an open-source **Sovereign Node Kit**: software,
reference configurations, reproducible benchmarks, and deployment guidance that
make personally or community-owned AI compute easier to inventory, configure,
operate, and audit without silently depending on a hosted provider.

## What this prototype does now

`node_doctor.py` performs a read-only capability inspection and emits a JSON
receipt containing:

- operating system and Python version;
- logical CPU count and physical RAM;
- NVIDIA GPU model/VRAM/driver when `nvidia-smi` is available;
- presence of common local-runtime tools such as Ollama, Docker, and Podman;
- a conservative local-workload profile; and
- explicit safety metadata confirming that the doctor does not install
  software, call the network, read credentials, or open listening ports.

Run:

```bash
python node_doctor.py
python node_doctor.py --write evidence/node-capability.json
python -m unittest -v
```

## Why this is useful but not sufficient

A deployable local-compute node needs much more than hardware detection. The
grant-sized project would add:

1. reproducible install/configuration plans for several hardware tiers;
2. local inference runtime adapters with fail-closed local routing;
3. health checks, queueing, resource limits, and update/rollback receipts;
4. reproducible performance/energy/cost benchmarks;
5. privacy and threat-model guidance;
6. a small pilot with ordinary users/builders;
7. an economic model covering ownership cost, utilization, and optional idle
   compute sharing; and
8. documentation that an average technical user can follow without expert
   cluster administration.

The prototype deliberately does **not** claim that a complete local AI cluster,
business model, community pilot, or production security layer already exists.
