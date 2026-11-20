"""Create initial manifest metadata from authored topics, without rewriting prose."""
from pathlib import Path
import re
from urllib.parse import parse_qs
from common import read, relative, write
from markdown_links import block_links


def prepare(root, title, manuscript="publication/reading.md"):
    root = Path(root).resolve()
    target = root / "content/manifest.json"
    if target.exists():
        raise ValueError("Manifest already exists; edit it deliberately instead of overwriting metadata")
    run = read(root / "run.json")
    sources = {s["id"] for s in read(root / "sources.json")}
    topics, seen = [], set()
    for path in sorted((root / "content/topics").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        heading = re.search(r"^# (.+)$", text, re.M)
        if not heading:
            raise ValueError(f"Missing topic title in {path.name}")
        blocks = []
        for ident, targets in block_links(text).items():
            if ident in seen:
                raise ValueError(f"Duplicate block ID: {ident}")
            seen.add(ident)
            refs = []
            for link in targets:
                if not link.startswith("source:") or "#" not in link:
                    continue
                source_id, fragment = link[7:].split("#", 1)
                if source_id not in sources:
                    raise ValueError(f"Unknown source {source_id}")
                values = parse_qs(fragment)
                if "t" in values:
                    at = float(values["t"][0])
                    ref = {"source": source_id, "start": at, "end": at}
                else:
                    locator = {k: int(v[0]) for k,v in values.items() if k in ("page","slide","paragraph","line","table")}
                    if not locator:
                        raise ValueError(f"Unsupported locator: {link}")
                    ref = {"source": source_id, "locator": locator}
                if ref not in refs:
                    refs.append(ref)
            if not refs:
                raise ValueError(f"No rendered source citation for block {ident}")
            blocks.append({"id": ident, "sources": refs})
        if not blocks:
            raise ValueError(f"No content blocks in {path.name}")
        topics.append({"id": path.stem, "title": heading.group(1), "summary": heading.group(1),
                       "path": relative(root, path), "blocks": blocks})
    if not topics:
        raise ValueError("Write marked content/topics/*.md first")
    value = {"schema_version": 1, "language": run["language"], "title": title,
             "manuscript": manuscript, "topics": topics, "evidence": [], "limitations": ""}
    write(target, value)
    return {"manifest": relative(root,target), "topics": len(topics), "blocks": len(seen),
            "next": "Review order/summaries, expand time points to supported intervals, add evidence and limitations; author the manuscript and coverage before check."}
