"""Publication validation, Markdown export, and two-step Pandoc/Typst build."""
from pathlib import Path
import re
import shutil
from urllib.parse import quote, unquote, urlsplit

from common import (execute, fingerprint, inside, interval, lines, operation, read,
                    relative, sha, source, version, write)

LINK = re.compile(r'(!?\[[^\]\n]*\])\((<[^>\n]+>|[^\s)]+)(\s+"[^"\n]*")?\)')
MARKER = re.compile(r'<!--\s*block:([a-zA-Z0-9_-]+)\s*-->')


def content_inputs(root):
    root = Path(root)
    manifest = root / "content" / "manifest.json"
    data = read(manifest)
    paths = [manifest, root / "sources.json", root / "review" / "coverage.json", inside(root, data["manuscript"])]
    paths += [inside(root, topic["path"]) for topic in data["topics"]]
    paths += [inside(root, p) for p in data.get("evidence", [])]
    paths += [p for p in (root / "review").rglob("*") if p.is_file() and p not in paths]
    # Every local link is a dependency, including images. Follow only existing files.
    for path in list(paths):
        if path.suffix == ".md":
            for match in LINK.finditer(path.read_text(encoding="utf-8")):
                target = match.group(2).strip("<>")
                if not urlsplit(target).scheme and not target.startswith("#"):
                    dependency = (path.parent / unquote(target.split("#", 1)[0])).resolve()
                    if dependency.is_file() and dependency not in paths:
                        paths.append(dependency)
    inputs = {relative(root, p): sha(p) for p in paths}
    inputs["agreement"] = fingerprint(read(root / "run.json").get("agreement"))
    run = read(root / "run.json")
    inputs["run_settings"] = fingerprint({"scope": run["scope"], "language": run["language"]})
    return data, inputs


def validate(root):
    root = Path(root).resolve()
    errors, warnings = [], []
    run = read(root / "run.json")
    sources = {s["id"]: s for s in read(root / "sources.json")}
    for source_id in sources:
        try:
            source(root, source_id)
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    if not run.get("agreement", {}).get("response"):
        errors.append("Record the user's actual structure confirmation in run.json: agreement.response")
    try:
        data, inputs = content_inputs(root)
    except (KeyError, OSError, ValueError) as exc:
        return {"passed": False, "errors": errors + [str(exc)], "warnings": warnings}
    if not data.get("language") or data["language"] != run.get("language"):
        errors.append("Content language must match the agreed result language")
    manuscript = inside(root, data["manuscript"])
    manuscript_text = manuscript.read_text(encoding="utf-8")
    pdf_blocks = MARKER.findall(manuscript_text)
    all_blocks = []
    ids = set()
    texts = [(manuscript, manuscript_text)]
    for topic in data["topics"]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", topic["id"]) or topic["id"] in ids:
            errors.append(f"Invalid or duplicate topic ID: {topic['id']}")
        ids.add(topic["id"])
        path = inside(root, topic["path"])
        text = path.read_text(encoding="utf-8")
        texts.append((path, text))
        marked = MARKER.findall(text)
        declared = [b["id"] for b in topic["blocks"]]
        if sorted(marked) != sorted(declared):
            errors.append(f"Block markers differ from manifest in {topic['id']}")
        for block in topic["blocks"]:
            all_blocks.append(block["id"])
            if not block.get("sources"):
                errors.append(f"No source for block {block['id']}")
            for ref in block.get("sources", []):
                item = sources.get(ref.get("source"))
                if item is None:
                    errors.append(f"Unknown source in {block['id']}: {ref}")
                    continue
                if "start" in ref or "end" in ref:
                    try:
                        interval(ref["start"], ref["end"], 0, item["duration"])
                    except (ValueError, KeyError) as exc:
                        errors.append(f"Bad source interval in {block['id']}: {exc}")
                elif not ref.get("locator"):
                    errors.append(f"Missing source locator in {block['id']}")
                else:
                    for key in ("page", "slide", "paragraph", "line", "table"):
                        if key in ref["locator"] and (not isinstance(ref["locator"][key], int) or ref["locator"][key] < 1):
                            errors.append(f"Invalid one-based {key} locator in {block['id']}")
    if not all_blocks or len(all_blocks) != len(set(all_blocks)):
        errors.append("Content blocks must be nonempty and have unique IDs")
    if sorted(pdf_blocks) != sorted(all_blocks):
        errors.append("PDF manuscript must include each declared content block once")
    for path, text in texts:
        for match in LINK.finditer(text):
            target = match.group(2).strip("<>")
            if target.startswith("source:"):
                source_id = target[7:].split("#", 1)[0]
                if source_id not in sources:
                    errors.append(f"Unknown linked source {source_id}")
                elif "#t=" in target:
                    try:
                        at = float(target.split("#t=", 1)[1])
                        interval(at, at, 0, sources[source_id]["duration"])
                    except (ValueError, KeyError) as exc:
                        errors.append(f"Invalid time link {target}: {exc}")
            elif urlsplit(target).scheme:
                if match.group(1).startswith("!"):
                    errors.append(f"Freeze remote images locally before publication: {target}")
            elif not target.startswith("#"):
                local = (path.parent / unquote(target.split("#", 1)[0])).resolve()
                try:
                    local.relative_to(root)
                except ValueError:
                    errors.append(f"Use source: links for external originals: {target}")
                if not local.is_file():
                    errors.append(f"Missing linked file in {relative(root, path)}: {target}")
        if re.search(r"^\s*\[[^\]]+\]:", text, flags=re.M):
            errors.append(f"Use inline Markdown links for export: {relative(root, path)}")
    try:
        coverage = read(root / "review" / "coverage.json")
        cursor = run["scope"][0]
        for item in sorted(coverage, key=lambda x: x["start"]):
            interval(item["start"], item["end"], *run["scope"])
            if item["start"] > cursor + 0.05:
                errors.append(f"Unaccounted interval at {cursor}")
            cursor = max(cursor, item["end"])
            if item["kind"] not in ("content", "repeat", "silence", "gap"):
                errors.append("Invalid coverage kind")
            if item["kind"] in ("content", "repeat") and (not item.get("blocks") or
                    any(b not in all_blocks for b in item["blocks"])):
                errors.append(f"Unlinked content interval: {item}")
            if item["kind"] == "gap":
                warnings.append(f"Unresolved gap: {item['start']}-{item['end']}: {item.get('note', '')}")
                if not item.get("note") or not data.get("limitations"):
                    errors.append("A coverage gap needs a note and visible publication limitations")
        if cursor < run["scope"][1] - 0.05:
            errors.append(f"Unaccounted interval at {cursor}")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(f"Invalid coverage: {exc}")
    for path in [inside(root, p) for p in data.get("evidence", []) if p.endswith("segments.jsonl")]:
        previous = -1
        for segment in lines(path):
            try:
                interval(segment["start"], segment["end"], *run["scope"])
                if segment["start"] < previous:
                    errors.append(f"Backward ASR start in {path.name}")
                previous = segment["start"]
            except (KeyError, ValueError) as exc:
                errors.append(str(exc))
    return {"passed": not errors, "errors": errors, "warnings": warnings,
            "content_revision": fingerprint(inputs), "inputs": inputs}


def build(root, pandoc="pandoc", typst="typst", font="Arial", size=11):
    root = Path(root).resolve()
    report = validate(root)
    write(root / "checks" / "structure.json", report)
    if not report["passed"]:
        raise ValueError("Content validation failed; see checks/structure.json")
    data, inputs = content_inputs(root)
    if not 6 <= size <= 40:
        raise ValueError("Font size must be between 6 and 40 points")
    sources = {s["id"]: s for s in read(root / "sources.json")}
    folder = root / "output"
    params = {"pandoc": pandoc, "typst": typst, "font": font, "size": size,
              "versions": {"pandoc": version(pandoc), "typst": version(typst)}}
    def action():
        previous = read(folder / "build.json").get("files", {}) if (folder / "build.json").exists() else {}
        folder.mkdir(parents=True, exist_ok=True)
        topics_dir = folder / "topics"
        topics_dir.mkdir(exist_ok=True)
        assets = folder / "assets"
        assets.mkdir(exist_ok=True)
        files = []
        topics = {inside(root, t["path"]): t["id"] + ".md" for t in data["topics"]}
        def export(path, destination, pdf=False):
            text = path.read_text(encoding="utf-8")
            def link(match):
                target = match.group(2).strip("<>")
                suffix = match.group(3) or ""
                if target.startswith("source:"):
                    source_id, _, fragment = target[7:].partition("#")
                    target = Path(sources[source_id]["path"]).as_uri() + ("#"+fragment if fragment else "")
                elif not urlsplit(target).scheme and not target.startswith("#"):
                    name, _, fragment = target.partition("#")
                    local = (path.parent / unquote(name)).resolve()
                    if local in topics:
                        copied = topics_dir / topics[local]
                    else:
                        copied = assets / (sha(local)[:12] + local.suffix.lower())
                        shutil.copy2(local, copied)
                        if copied not in files:
                            files.append(copied)
                    import os
                    target = Path(os.path.relpath(copied, destination.parent)).as_posix()
                    if fragment:
                        target += "#" + fragment
                return match.group(1) + "(<" + target + ">" + suffix + ")"
            text = LINK.sub(link, text)
            text = MARKER.sub("", text)
            if data.get("limitations"):
                limitation = data["limitations"].strip() + "\n\n"
                if pdf:
                    frontmatter = re.match(r"\A---\s*\n.*?\n---[ \t]*\n", text, re.S)
                    position = frontmatter.end() if frontmatter else 0
                    text = text[:position] + "\n" + limitation + text[position:]
                else:
                    text += "\n\n" + limitation
            destination.write_text(text, encoding="utf-8")
            files.append(destination)
        for topic in data["topics"]:
            export(inside(root, topic["path"]), topics_dir / (topic["id"] + ".md"))
        index = folder / "index.md"
        index.write_text("# " + data["title"] + "\n\n" + "\n".join(
            f"- [{t['title']}](topics/{t['id']}.md): {t['summary']}" for t in data["topics"]) +
            "\n\n" + data.get("limitations", "") + "\n", encoding="utf-8")
        files.append(index)
        export(inside(root, data["manuscript"]), folder / "reading.md", pdf=True)
        execute([pandoc, "reading.md", "--standalone", "--toc", "-t", "typst", "-V", f"fontsize={size}pt",
                 "-V", f"mainfont={font}", "-o", "digest.typ"], root / "checks" / "pandoc.log", folder)
        # Typst's default root is the input directory, so assets stay under output/.
        execute([typst, "compile", "digest.typ", "digest.pdf"], root / "checks" / "typst.log", folder)
        pdf = folder / "digest.pdf"
        if not pdf.read_bytes().startswith(b"%PDF-"):
            raise ValueError("The renderer did not produce a PDF")
        files.extend([folder / "digest.typ", pdf])
        current_paths = {relative(root, p) for p in files}
        for name in set(previous) - current_paths:
            obsolete = inside(root, name)
            obsolete.relative_to(folder)
            if obsolete.is_file():
                obsolete.unlink()
        write(folder / "build.json", {"content_revision": report["content_revision"], "format": params,
                                      "files": {relative(root, p): sha(p) for p in files}})
        files.append(folder / "build.json")
        return files
    return operation(root, "publication", inputs, params, action)


def review(root, kind, note):
    root = Path(root)
    report = validate(root)
    if not report["passed"]:
        raise ValueError("Fix structural errors before recording a completed review")
    if not note.strip():
        raise ValueError("Describe the review actually performed and any limitations")
    item = {"kind": kind, "content_revision": report["content_revision"], "note": note,
            "performed_by": "agent", "status": "passed"}
    if kind == "visual":
        item["pdf_sha256"] = sha(root / "output" / "digest.pdf")
    write(root / "checks" / f"{kind}-review.json", item)
    return item


def release(root):
    root = Path(root)
    report = validate(root)
    errors = list(report["errors"])
    if read(root / "run.json")["operations"].get("publication", {}).get("state") != "completed":
        errors.append("The last publication operation did not complete")
    try:
        built = read(root / "output" / "build.json")
        if built["content_revision"] != report.get("content_revision"):
            errors.append("Publication is stale")
        for path, digest in built["files"].items():
            if not inside(root, path).is_file() or sha(inside(root, path)) != digest:
                errors.append(f"Published artifact changed: {path}")
        for kind in ("content", "visual"):
            item = read(root / "checks" / f"{kind}-review.json")
            if item["content_revision"] != report.get("content_revision") or item["status"] != "passed":
                errors.append(f"Missing or stale {kind} review")
            if kind == "visual" and item["pdf_sha256"] != sha(root / "output" / "digest.pdf"):
                errors.append("Visual review refers to an older PDF")
    except (OSError, KeyError, ValueError) as exc:
        errors.append(str(exc))
    result = {"state": "ready" if not errors else "draft", "errors": errors,
              "limitations": report.get("warnings", []), "content_revision": report.get("content_revision")}
    write(root / "checks" / "release.json", result)
    return result
