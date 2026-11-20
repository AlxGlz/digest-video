#!/usr/bin/env python3
"""File-based helpers for digest-video. Run --help; content authoring stays with the agent."""
from pathlib import Path
import argparse
import importlib.metadata
import shutil
import sys

from common import emit, fingerprint, inside, interval, probe, read, sha, version, write


def register(root, source_id, path, video=False, ffprobe="ffprobe"):
    import re
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", source_id):
        raise ValueError("Source IDs use lowercase letters, numbers, and hyphens")
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"File unavailable: {path}")
    registry = Path(root) / "sources.json"
    sources = read(registry) if registry.exists() else []
    old = next((s for s in sources if s["id"] == source_id), {})
    item = {"id": source_id, "name": path.name, "path": str(path), "sha256": sha(path),
            "format": path.suffix.lower(), "role": "recording" if video or old.get("role") == "recording" else "attachment"}
    if item["role"] == "recording":
        metadata = probe(path, ffprobe)
        item["duration"] = float(metadata["format"]["duration"])
        item["media"] = metadata
        item["probe_version"] = version(ffprobe, "-version")
    if old and old["sha256"] != item["sha256"]:
        item["previous_revisions"] = old.get("previous_revisions", []) + [{"sha256": old["sha256"], "path": old["path"]}]
    elif old.get("previous_revisions"):
        item["previous_revisions"] = old["previous_revisions"]
    write(registry, [s for s in sources if s["id"] != source_id] + [item])
    return item


def init(args):
    root = Path(args.work).resolve()
    if root.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("Keep private run data outside the skill directory")
    if (root / "run.json").exists():
        raise ValueError("This run already exists. Use status and resume it, or choose a new working directory")
    root.mkdir(parents=True, exist_ok=True)
    item = register(root, "video", args.video, True, args.ffprobe)
    end = item["duration"] if args.end is None else args.end
    interval(args.start, end, 0, item["duration"])
    if end <= args.start:
        raise ValueError("Require a nonempty scope")
    for name in ("evidence", "review", "content/topics", "publication", "checks"):
        (root / name).mkdir(parents=True, exist_ok=True)
    run = {"schema_version": 1, "video": "video", "scope": [args.start, end],
           "language": args.language, "agreement": {}, "operations": {}}
    write(root / "run.json", run)
    return {"work": str(root), "scope": run["scope"], "source": item["id"]}


def status(root):
    root = Path(root)
    run = read(root / "run.json")
    sources = read(root / "sources.json")
    result = {"scope": run["scope"], "language": run["language"], "agreement": run["agreement"],
              "sources": [], "operations": {}}
    current = {}
    for src in sources:
        current[src["id"]] = sha(src["path"]) if Path(src["path"]).is_file() else None
        result["sources"].append({"id": src["id"], "state": "unchanged" if current[src["id"]] == src["sha256"] else "changed-or-missing"})
    for key, op in run["operations"].items():
        state = op["state"]
        if state == "completed":
            for name, digest in op["inputs"].items():
                if name in current and current[name] != digest:
                    state = "stale"
                elif name == "agreement":
                    if fingerprint(run.get("agreement")) != digest:
                        state = "stale"
                elif name == "run_settings":
                    if fingerprint({"scope": run["scope"], "language": run["language"]}) != digest:
                        state = "stale"
                elif name not in current:
                    path = root / name
                    if not path.is_file() or sha(path) != digest:
                        state = "stale"
            for name, digest in op.get("outputs", {}).items():
                path = inside(root, name)
                if not path.is_file() or sha(path) != digest:
                    state = "stale"
        result["operations"][key] = state
    return result


def doctor():
    packages = {}
    for package in ("faster-whisper", "ctranslate2", "av", "pypdf", "pypdfium2", "python-docx", "python-pptx", "markitdown"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    return {"python": sys.version, "commands": {x: shutil.which(x) for x in ("ffmpeg", "ffprobe", "pandoc", "typst", "soffice", "tesseract")},
            "packages": packages, "note": "The agent must separately establish available audio and image understanding capabilities."}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", default=".", help="Run directory, outside the skill checkout")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("status")
    x = sub.add_parser("init")
    x.add_argument("--video", required=True)
    x.add_argument("--language", required=True, help="Result language, such as ru or en")
    x.add_argument("--start", type=float, default=0)
    x.add_argument("--end", type=float)
    x.add_argument("--ffprobe", default="ffprobe")
    x = sub.add_parser("source", help="Register an attachment or refresh/relocate a source")
    x.add_argument("id")
    x.add_argument("path")
    x.add_argument("--ffprobe", default="ffprobe")
    x = sub.add_parser("agreement", help="Import the actual user-confirmed structure")
    x.add_argument("file")
    x = sub.add_parser("audio")
    x.add_argument("--start", type=float)
    x.add_argument("--end", type=float)
    x.add_argument("--ffmpeg", default="ffmpeg")
    x = sub.add_parser("frame")
    x.add_argument("--at", required=True, type=float)
    x.add_argument("--width", type=int, default=1600)
    x.add_argument("--ffmpeg", default="ffmpeg")
    x = sub.add_parser("transcribe")
    x.add_argument("--model", required=True, help="Existing faster-whisper model directory")
    x.add_argument("--language", required=True, help="Spoken language; may differ from result language")
    x.add_argument("--chunk", type=float, default=300)
    x.add_argument("--overlap", type=float, default=4)
    x.add_argument("--threads", type=int, default=4)
    x.add_argument("--vad", action="store_true")
    x.add_argument("--start", type=float)
    x.add_argument("--end", type=float)
    x.add_argument("--ffmpeg", default="ffmpeg")
    x = sub.add_parser("document")
    x.add_argument("source")
    x.add_argument("--reader", choices=("auto", "text", "pdf", "docx", "pptx", "markitdown"), default="auto")
    x = sub.add_parser("render")
    x.add_argument("--pdf", help="PDF to render; default is output/digest.pdf")
    x.add_argument("--source", help="Registered PDF source ID")
    x.add_argument("--pages", help="Comma-separated one-based page numbers; default all")
    x.add_argument("--width", type=int, default=1600)
    sub.add_parser("check")
    x = sub.add_parser("build")
    x.add_argument("--pandoc", default="pandoc")
    x.add_argument("--typst", default="typst")
    x.add_argument("--font", default="Arial")
    x.add_argument("--size", type=float, default=11)
    x = sub.add_parser("review", help="Record a review actually performed; does not perform the review")
    x.add_argument("kind", choices=("content", "visual"))
    x.add_argument("--note", required=True)
    sub.add_parser("release")
    return p


def main():
    args = parser().parse_args()
    root = Path(args.work).resolve()
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "init":
            result = init(args)
        elif args.command == "source":
            result = register(root, args.id, args.path, ffprobe=args.ffprobe)
        elif args.command == "status":
            result = status(root)
        elif args.command == "agreement":
            value = read(args.file)
            if not all(value.get(k) for k in ("type", "sections", "response")):
                raise ValueError("Agreement needs type, sections, and the user's actual response")
            run = read(root / "run.json")
            run["agreement"] = value
            write(root / "run.json", run)
            result = {"agreement": value}
        elif args.command == "audio":
            from media import audio
            path, result = audio(root, args.start, args.end, args.ffmpeg)
        elif args.command == "frame":
            from media import frame
            result = frame(root, args.at, args.ffmpeg, args.width)
        elif args.command == "transcribe":
            from media import transcribe
            result = transcribe(root, args.model, args.language, args.chunk, args.overlap, args.threads,
                                args.vad, args.start, args.end, args.ffmpeg)
        elif args.command == "document":
            from documents import extract
            result = extract(root, args.source, args.reader)
        elif args.command == "render":
            from common import source
            from documents import render
            pdf = args.pdf or (source(root, args.source)["path"] if args.source else root / "output/digest.pdf")
            result = render(root, pdf, [int(x) for x in args.pages.split(",")] if args.pages else None, args.width, args.source)
        else:
            from publication import build, release, review, validate
            if args.command == "check":
                result = validate(root)
                write(root / "checks/structure.json", result)
            elif args.command == "build":
                result = build(root, args.pandoc, args.typst, args.font, args.size)
            elif args.command == "review":
                result = review(root, args.kind, args.note)
            else:
                result = release(root)
        emit(result)
        if result.get("passed") is False or result.get("state") == "draft":
            return 1
        return 0
    except Exception as exc:
        emit({"error": str(exc), "type": type(exc).__name__})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
