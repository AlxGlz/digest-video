"""Shared run storage and content-addressed operation records (stdlib only)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def relative(root, path):
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def inside(root, path):
    root = Path(root).resolve()
    result = (root / path).resolve()
    result.relative_to(root)
    return result


def run_file(root):
    return Path(root) / "run.json"


def source(root, source_id, verify=True):
    item = next((s for s in read(Path(root) / "sources.json") if s["id"] == source_id), None)
    if not item:
        raise ValueError(f"Unknown source: {source_id}")
    path = Path(item["path"])
    if not path.is_file():
        raise ValueError(f"Source unavailable: {path}. Relocate it using the source command.")
    if verify and sha(path) != item["sha256"]:
        raise ValueError(f"Source changed: {source_id}. Register its new revision with the source command.")
    return item


def execute(command, log, cwd=None):
    result = subprocess.run([str(x) for x in command], cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
    Path(log).parent.mkdir(parents=True, exist_ok=True)
    Path(log).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); see {log}")
    return result.stdout, result.stderr


def probe(path, ffprobe="ffprobe"):
    result = subprocess.run([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                            capture_output=True, encoding="utf-8", errors="replace", check=True)
    return json.loads(result.stdout)


def version(executable, flag="--version"):
    result = subprocess.run([str(executable), flag], capture_output=True, encoding="utf-8", errors="replace", check=True)
    return (result.stdout or result.stderr).splitlines()[0]


def code_revision():
    return fingerprint({p.name: sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))})


def operation(root, key, inputs, params, action):
    """Only checked, unchanged outputs are reused. Failed attempts remain resumable."""
    root = Path(root).resolve()
    run = read(run_file(root))
    signature = fingerprint({"inputs": inputs, "params": params, "code": code_revision()})
    old = run["operations"].get(key, {})
    outputs = old.get("outputs", {})
    if (old.get("state") == "completed" and old.get("signature") == signature and outputs
            and all(inside(root, p).is_file() and sha(inside(root, p)) == h for p, h in outputs.items())):
        return {"cached": True, "operation": key, "files": list(outputs)}
    record = {"state": "running", "signature": signature, "inputs": inputs, "params": params,
              "started_at": time.time()}
    run["operations"][key] = record
    write(run_file(root), run)
    try:
        files = list(action())
        if not files:
            raise ValueError("Operation produced no artifacts")
        hashes = {relative(root, p): sha(p) for p in files}
        record.update(state="completed", outputs=hashes, finished_at=time.time())
    except Exception as exc:
        record.update(state="blocked", error=str(exc))
        run = read(run_file(root))
        run["operations"][key] = record
        write(run_file(root), run)
        raise
    run = read(run_file(root))
    run["operations"][key] = record
    write(run_file(root), run)
    return {"cached": False, "operation": key, "files": list(hashes)}


def dump_lines(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    os.replace(temp, path)


def lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def interval(start, end, lower, upper):
    import math
    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in (start, end)):
        raise ValueError("Times must be finite numbers")
    if not lower <= start <= end <= upper + 0.05:
        raise ValueError(f"Invalid interval [{start}, {end}] within [{lower}, {upper}]")


def emit(value):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, indent=2))
