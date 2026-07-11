from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from harness.engine.bounded_process import BoundedProcessError, run_bounded_process


def run_legacy_validator(root: Path) -> dict[str, Any]:
    try:
        with tempfile.TemporaryDirectory(
            prefix="legacy-validator-",
            dir="/tmp",
        ) as temporary:
            control_root = Path(temporary)
            home = control_root / "home"
            xdg = control_root / "xdg"
            runtime_tmp = control_root / "tmp"
            for directory in (home, xdg, runtime_tmp):
                directory.mkdir()
            environment = {
                key: value
                for key, value in os.environ.items()
                if key == "LANG" or key.startswith("LC_")
            }
            environment.update(
                {
                    "PATH": os.defpath,
                    "HOME": str(home),
                    "XDG_CONFIG_HOME": str(xdg),
                    "TMPDIR": str(runtime_tmp),
                    "TMP": str(runtime_tmp),
                    "TEMP": str(runtime_tmp),
                    "PYTHONUTF8": "1",
                    "PYTHONNOUSERSITE": "1",
                    "PYTHONSAFEPATH": "1",
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_ATTR_NOSYSTEM": "1",
                    "GIT_LITERAL_PATHSPECS": "1",
                    "GIT_TERMINAL_PROMPT": "0",
                }
            )
            completed = run_bounded_process(
                root,
                [
                    sys.executable,
                    "scripts/validate_benchmark_kb.py",
                    "--no-write-report",
                ],
                label="legacy validator",
                timeout=120,
                environment=environment,
            )
    except BoundedProcessError as exc:
        raise RuntimeError(f"legacy validator subprocess {exc.code}") from exc
    except OSError as exc:
        raise RuntimeError("legacy validator subprocess launch failed") from exc
    if not completed.stdout.strip():
        raise RuntimeError("legacy validator returned no JSON")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("legacy validator returned invalid JSON") from exc
    result["process_exit_code"] = completed.returncode
    return result
