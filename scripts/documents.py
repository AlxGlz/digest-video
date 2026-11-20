"""Optional document readers. Native environment tools may supply the same records."""
from pathlib import Path
import importlib.metadata
import time

from common import operation, read, relative, sha, source, write


def extract(root, source_id, reader="auto"):
    root = Path(root)
    src = source(root, source_id)
    path = Path(src["path"])
    extension = path.suffix.lower()
    reader = {".pdf": "pdf", ".docx": "docx", ".pptx": "pptx"}.get(extension, "text") if reader == "auto" else reader
    packages = {"pdf": "pypdf", "docx": "python-docx", "pptx": "python-pptx", "markitdown": "markitdown"}
    version = importlib.metadata.version(packages[reader]) if reader in packages else "stdlib"
    def action():
        folder = root / "evidence" / "documents" / source_id / str(time.time_ns())
        folder.mkdir(parents=True, exist_ok=True)
        records, images, warnings, files = [], [], [], []
        def add(locator, text, kind="text"):
            records.append({"source": source_id, "locator": locator, "kind": kind, "text": text})
        def picture(blob, extension, locator):
            target = folder / f"image-{len(images)+1:04}.{extension}"
            target.write_bytes(blob)
            images.append({"source": source_id, "locator": locator, "path": relative(root, target)})
            files.append(target)
        if reader == "pdf":
            from pypdf import PdfReader
            document = PdfReader(path)
            for i, page in enumerate(document.pages, 1):
                text = page.extract_text() or ""
                add({"page": i}, text)
                if not text.strip():
                    warnings.append(f"Page {i}: no text; inspect its rendering and use available OCR if needed.")
            warnings.append("Text extraction does not verify columns, formulas, tables, or images. Render relevant pages.")
        elif reader == "docx":
            from docx import Document
            from docx.text.paragraph import Paragraph
            document = Document(path)
            paragraph, table = 0, 0
            for item in document.iter_inner_content():
                if isinstance(item, Paragraph):
                    paragraph += 1
                    add({"paragraph": paragraph, "style": item.style.name if item.style else ""}, item.text)
                else:
                    table += 1
                    add({"table": table}, "\n".join("\t".join(c.text for c in row.cells) for row in item.rows), "table")
            for relation in document.part.rels.values():
                if not relation.is_external and "image" in relation.reltype:
                    part = relation.target_part
                    picture(part.blob, Path(str(part.partname)).suffix.lstrip("."), {"relationship": relation.rId})
            warnings.append("Main body and embedded images extracted; render relevant passages to check equations, text boxes, headers, tracked edits, and layout. Image relationships are not page locators.")
        elif reader == "pptx":
            from pptx import Presentation
            document = Presentation(path)
            def shapes(items, slide, prefix=""):
                for shape in items:
                    locator = {"slide": slide, "shape": prefix + str(shape.shape_id)}
                    if shape.has_text_frame:
                        add(locator, shape.text)
                    if shape.has_table:
                        add(locator, "\n".join("\t".join(c.text for c in row.cells) for row in shape.table.rows), "table")
                    if hasattr(shape, "image"):
                        picture(shape.image.blob, shape.image.ext, locator)
                    if shape.has_chart:
                        warnings.append(f"Slide {slide}, shape {shape.shape_id}: chart requires rendering or a chart-aware reader.")
                    if hasattr(shape, "shapes"):
                        shapes(shape.shapes, slide, locator["shape"] + "/")
            for i, slide in enumerate(document.slides, 1):
                shapes(slide.shapes, i)
                if slide.has_notes_slide:
                    notes = slide.notes_slide.notes_text_frame
                    if notes is not None:
                        add({"slide": i, "part": "speaker_notes"}, notes.text, "notes")
            warnings.append("Extracted objects are not slide renderings. Render slides for composition, diagrams, and animations; speaker notes are attachment content, not evidence of spoken words.")
        elif reader == "markitdown":
            from markitdown import MarkItDown
            add({"file": path.name}, MarkItDown().convert(str(path)).text_content)
            warnings.append("Generic conversion has file-level provenance only. Recover precise locators and inspect significant objects before citing.")
        else:
            raw = path.read_bytes()
            if b"\x00" in raw:
                raise ValueError("Binary input: select an available format-aware reader instead of treating it as text")
            text = raw.decode("utf-8-sig")
            for i, line in enumerate(text.splitlines(), 1):
                add({"line": i}, line)
        output = folder / "document.json"
        write(output, {"source": source_id, "source_sha256": src["sha256"], "reader": reader, "version": version,
                       "status": "partial" if warnings else "extracted", "records": records,
                       "images": images, "limitations": warnings})
        return files + [output]
    return operation(root, f"document:{source_id}:{reader}", {source_id: src["sha256"]},
                     {"reader": reader, "version": version}, action)


def render(root, pdf, pages=None, width=1600, source_id=None):
    import pypdfium2 as pdfium
    root = Path(root).resolve()
    pdf = Path(pdf).resolve()
    if width < 100:
        raise ValueError("Page width must be at least 100 pixels")
    digest = sha(pdf)
    folder = root / "evidence" / "pages" / digest[:12] if source_id else root / "checks" / "pages" / digest[:12]
    with pdfium.PdfDocument(str(pdf)) as document:
        selected = list(range(1, len(document)+1)) if pages is None else pages
        if not selected or any(n < 1 or n > len(document) for n in selected):
            raise ValueError("Page numbers are one-based and must exist")
    params = {"pages": selected, "width": width, "version": importlib.metadata.version("pypdfium2")}
    def action():
        folder.mkdir(parents=True, exist_ok=True)
        files, records = [], []
        with pdfium.PdfDocument(str(pdf)) as document:
            for n in selected:
                page = document[n-1]
                bitmap = page.render(scale=width/page.get_width())
                target = folder / f"page-{n:04}.png"
                bitmap.to_pil().save(target)
                bitmap.close()
                page.close()
                records.append({"source": source_id, "pdf_sha256": digest, "page": n,
                                "path": relative(root, target)})
                files.append(target)
        index = folder / ("index-" + str(width) + "-" + str(selected[0]) + "-" + str(selected[-1]) + ".json")
        write(index, records)
        return files + [index]
    return operation(root, "pages:" + digest[:12] + ":" + str(selected), {str(pdf): digest}, params, action)
