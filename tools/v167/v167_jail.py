"""Per-task worker file-access guard installed with CPython's sys.addaudithook.

This is deliberately labelled NON-ADVERSARIAL RUNTIME ISOLATION, not an
operating-system sandbox: it proves that this workstation's estimator process
cannot reach controller-only data on its own code path, and it records every
refusal.  It does not stop a process that bypasses the interpreter (a raw
CreateFile syscall, a debugger, or an fd opened before installation).

Allow-list, per task:
  results/v167/estimator_inputs/<task>/   own projection only (read, write)
  results/v167/tasks/<task>/              own record tree only (read, write)
  tools/v167/                             own estimator modules (read)
  tools/v167_bundle/approved_core/        byte-verified frozen objective core (read)
  tools/v167_bundle/code/v167_payload_gate.py  single named estimator file (read)
  the interpreter install and its site-packages (read)
Anything else under results/, the whole v167_prepared staging tree, results/v166,
the parent workspace, .git objects and the network are refused.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# The guard's refusal type is defined once, in v167_common, so a refusal raised
# here is the same object the worker catches in probe mode and the controller
# records in its stop markers.  A local duplicate class would let a refusal
# escape the except clause as an unhandled error.
from v167_common import JailViolation

READ_OK: tuple[str, ...] = ()
WRITE_OK: tuple[str, ...] = ()
DENIED_READ: tuple[str, ...] = ()
DENIED_MODULE_PREFIXES = (
    "v165_io", "v165_run", "v165_guard", "v165_task_ids", "v165_validator",
    "v166", "v167_plan", "v167_controller", "v167_service", "v167_jail_probe",
    "v167_runner", "v167_validator", "v167_production", "run_all",
    "socket", "ssl", "urllib", "http", "ftplib", "smtplib", "poplib", "imaplib",
    "telnetlib", "subprocess", "multiprocessing", "asyncio", "ctypes",
    "h5py", "git", "requests", "paramiko",
)
DENIED_EVENTS_ALWAYS = frozenset({
    "os.system", "os.exec", "os.spawn", "os.startfile", "os.fork",
    "popen", "exe", "launch", "webbrowser.open", "ctypes", "tempfile.mktemp",
})


class JailLog(list):
    def record(self, event: str, target: object, reason: str) -> None:
        self.append({"event": event, "target": str(target), "reason": reason})


LOG = JailLog()


def _under(candidate: str, roots: tuple[str, ...]) -> bool:
    for root in roots:
        if candidate == root or candidate.startswith(root + os.sep):
            return True
    return False


def _normalise(raw: object) -> str | None:
    if isinstance(raw, (bytes, bytearray)):
        raw = os.fsdecode(bytes(raw))
    if not isinstance(raw, str):
        return None
    if raw in {"", "."} or raw.startswith("\\\\"):
        return None
    try:
        return os.path.normcase(os.path.abspath(raw))
    except Exception:
        return None


def install(allowed_read: list[str], allowed_write: list[str],
            denied_read: list[str] | None = None) -> dict:
    """Install the audit hook.  Returns the machine-readable jail contract."""
    global READ_OK, WRITE_OK, DENIED_READ
    READ_OK = tuple(os.path.normcase(os.path.abspath(str(p))) for p in allowed_read)
    WRITE_OK = tuple(os.path.normcase(os.path.abspath(str(p))) for p in allowed_write)
    # Controller-only sources live in the same directory as the estimator
    # modules, so an explicit deny is checked ahead of the allow-list.
    DENIED_READ = tuple(sorted(os.path.normcase(os.path.abspath(str(p)))
                               for p in (denied_read or [])))
    if not hasattr(sys, "addaudithook"):
        raise RuntimeError("AUDIT_HOOK_UNSUPPORTED")
    sys.addaudithook(_hook)
    return {
        "schema": "iscat167.worker_jail.1",
        "isolation_label": "PYTHON_LEVEL_AUDIT_HOOK_NOT_A_KERNEL_SANDBOX",
        "allowed_read_roots": list(READ_OK),
        "allowed_write_roots": list(WRITE_OK),
        "denied_read_paths": list(DENIED_READ),
        "denied_module_prefixes": list(DENIED_MODULE_PREFIXES),
        "denied_events": sorted(DENIED_EVENTS_ALWAYS),
        "note": "Descriptor-based reopen (os.fdopen on a pre-existing fd) and "
                "non-interpreter syscalls are outside this guard's reach and are "
                "reported as a residual limitation, not as proof.",
    }


def _check_path(event: str, raw: object, *, write: bool) -> None:
    path = _normalise(raw)
    if path is None:
        return
    if _under(path, DENIED_READ) or path in DENIED_READ:
        LOG.record(event, path, "DENIED_CONTROLLER_ONLY_SOURCE")
        raise JailViolation(f"WORKER_ACCESS_DENIED:{event}:{path}")
    roots = WRITE_OK if write else READ_OK
    if _under(path, roots):
        return
    if not write and _under(path, READ_OK):
        return
    LOG.record(event, path, "OUTSIDE_ALLOW_LIST")
    raise JailViolation(f"WORKER_ACCESS_DENIED:{event}:{path}")


def _deny_module(name: str) -> None:
    top = name.split(".")[0]
    for prefix in DENIED_MODULE_PREFIXES:
        if top == prefix.split(".")[0] and name.startswith(prefix):
            LOG.record("import", name, "DENIED_MODULE")
            raise JailViolation("WORKER_IMPORT_DENIED:" + name)


def _hook(event: str, args: tuple) -> None:
    if event == "open":
        # args = (path, mode, flags); an int path is an already-open fd.
        if isinstance(args[0], int):
            return
        if isinstance(args[1], str):
            writing = any(flag in args[1] for flag in ("w", "a", "+", "x"))
        elif isinstance(args[1], int):
            writing = bool(args[1] & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | getattr(os, "O_TRUNC", 0)))
        else:
            writing = False
        _check_path(event, args[0], write=writing)
        return
    if event in ("os.remove", "os.rmdir", "os.rename", "os.replace", "os.mkdir",
                 "os.truncate", "os.chmod", "shutil.copy", "shutil.copy_file",
                 "shutil.copytree", "shutil.move", "os.link", "os.symlink"):
        for value in args[:2]:
            _check_path(event, value, write=True)
        return
    if event in ("os.listdir", "os.scandir", "os.walk", "glob.glob", "pathlib.Path.glob",
                 "pathlib.Path.rglob", "os.stat", "os.getcwd"):
        _check_path(event, args[0] if args else os.getcwd(), write=False)
        return
    if event in ("subprocess.Popen", "os.system", "os.exec", "os.spawn",
                 "os.startfile", "os.fork", "webbrowser.open", "ctypes", "socket",
                 "socket.getaddrinfo", "socket.connect", "ssl.SSLContext", "tempfile.mktemp"):
        LOG.record(event, repr(args[:1]), "DENIED_EVENT")
        raise JailViolation("WORKER_EVENT_DENIED:" + event)
    if event == "import":
        _deny_module(str(args[0]))
        return
    if event == "sys.excepthook" or event == "warnings.options":
        return
    if event == "files.read":
        for item in (args[1] or ()):
            _check_path("files.read", item, write=False)
