"""HAL Open Local AI sovereign-node capability doctor.

This bounded prototype inventories a workstation without installing software,
opening sockets, reading credentials, or sending network traffic.  It emits a
portable JSON capability receipt and a conservative local-compute profile.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


def _memory_bytes() -> int | None:
    """Best-effort physical-memory discovery using the standard library."""
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
        return None

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        return int(page_size * pages)
    except (AttributeError, OSError, ValueError):
        return None


def parse_nvidia_smi(text: str) -> list[dict[str, Any]]:
    """Parse CSV rows: name, memory.total MiB, driver_version."""
    gpus: list[dict[str, Any]] = []
    for raw in text.splitlines():
        row = [part.strip() for part in raw.split(",")]
        if len(row) < 3:
            continue
        try:
            memory_mib = int(float(row[1]))
        except ValueError:
            memory_mib = None
        gpus.append(
            {
                "name": row[0],
                "memory_mib": memory_mib,
                "driver_version": row[2],
            }
        )
    return gpus


def _nvidia_gpus() -> list[dict[str, Any]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    try:
        proc = subprocess.run(
            [
                exe,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_nvidia_smi(proc.stdout)


def recommend_profile(
    total_ram_gib: float | None,
    gpu_memory_gib: list[float],
) -> dict[str, Any]:
    """Return a conservative workload profile, not a performance guarantee."""
    best_vram = max(gpu_memory_gib, default=0.0)
    if best_vram >= 24:
        profile = "gpu-large"
        model_hint = "quantized models roughly 14B-32B, subject to context/runtime"
    elif best_vram >= 12:
        profile = "gpu-medium"
        model_hint = "quantized models roughly 7B-14B, subject to context/runtime"
    elif best_vram >= 8:
        profile = "gpu-small"
        model_hint = "small/medium quantized models, subject to context/runtime"
    elif (total_ram_gib or 0) >= 32:
        profile = "cpu-small"
        model_hint = "small quantized models; expect materially higher latency"
    else:
        profile = "minimal"
        model_hint = "lightweight models or remote compute may be required"

    return {
        "profile": profile,
        "model_hint": model_hint,
        "guarantee": False,
    }


def inspect_node() -> dict[str, Any]:
    total_memory = _memory_bytes()
    gpus = _nvidia_gpus()
    total_ram_gib = round(total_memory / (1024**3), 2) if total_memory else None
    gpu_memory_gib = [
        round(gpu["memory_mib"] / 1024, 2)
        for gpu in gpus
        if isinstance(gpu.get("memory_mib"), int)
    ]

    tools = {}
    for name in ("ollama", "docker", "podman", "git", "python", "python3"):
        tools[name] = {"present": shutil.which(name) is not None}

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "cpu": {"logical_cores": os.cpu_count()},
        "memory": {
            "total_bytes": total_memory,
            "total_gib": total_ram_gib,
        },
        "gpus": gpus,
        "tools": tools,
        "recommended_profile": recommend_profile(total_ram_gib, gpu_memory_gib),
        "safety": {
            "network_calls": False,
            "installs_software": False,
            "reads_credentials": False,
            "opens_listening_ports": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a machine and emit a local-AI node capability receipt."
    )
    parser.add_argument("--write", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    receipt = inspect_node()
    rendered = json.dumps(receipt, indent=2, sort_keys=True)
    print(rendered)

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
