from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_OUTPUT_LIMIT = 1024 * 1024


class BoundedProcessError(RuntimeError):
    def __init__(self, code: str, label: str, *, returncode: int | None = None):
        self.code = code
        self.label = label
        self.returncode = returncode
        suffix = "" if returncode is None else f" (exit {returncode})"
        super().__init__(f"{label}: {code}{suffix}")


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if process.poll() is None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def run_bounded_process(
    root: Path,
    arguments: Sequence[str],
    *,
    label: str,
    timeout: int | float,
    environment: Mapping[str, str],
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
) -> subprocess.CompletedProcess[str]:
    if timeout <= 0 or output_limit <= 0:
        raise BoundedProcessError("invalid_limits", label)
    try:
        process = subprocess.Popen(
            list(arguments),
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=dict(environment),
        )
    except OSError as exc:
        raise BoundedProcessError("launch_failed", label) from exc
    if process.stdout is None or process.stderr is None:
        _kill_process_group(process)
        raise BoundedProcessError("pipe_setup_failed", label)

    streams = ((process.stdout, bytearray()), (process.stderr, bytearray()))
    selector: selectors.BaseSelector | None = None
    leader_cleaned = False
    try:
        selector = selectors.DefaultSelector()
        for stream, _ in streams:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        total = 0
        while selector.get_map():
            if process.poll() is not None and not leader_cleaned:
                _kill_process_group(process)
                leader_cleaned = True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BoundedProcessError("timeout", label)
            events = selector.select(min(remaining, 0.1))
            for key, _ in events:
                stream = key.fileobj
                try:
                    chunk = os.read(stream.fileno(), 64 * 1024)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                if len(chunk) > output_limit - total:
                    raise BoundedProcessError("output_limit_exceeded", label)
                target = streams[0][1] if stream is process.stdout else streams[1][1]
                target.extend(chunk)
                total += len(chunk)
        remaining = max(0.0, deadline - time.monotonic())
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise BoundedProcessError("timeout", label) from exc
    except BaseException:
        _kill_process_group(process)
        raise
    finally:
        # The leader may have exited while descendants retained inherited stdio.
        # Always target the original PGID, even when process.poll() is complete.
        _kill_process_group(process)
        if selector is not None:
            selector.close()
        for stream, _ in streams:
            try:
                stream.close()
            except OSError:
                pass
    return subprocess.CompletedProcess(
        args=list(arguments),
        returncode=returncode,
        stdout=streams[0][1].decode("utf-8", errors="replace"),
        stderr=streams[1][1].decode("utf-8", errors="replace"),
    )


__all__ = [
    "BoundedProcessError",
    "DEFAULT_OUTPUT_LIMIT",
    "run_bounded_process",
]
