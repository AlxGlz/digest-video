"""Behavioral tests using synthetic sources; no model downloads or private fixtures."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import fingerprint, inside, operation, read, sha, write
from digest import register, status
from media import normalize
from publication import content_inputs, release, review, validate


class RunCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "source.txt").write_text("Synthetic recording stand-in", encoding="utf-8")
        src = {"id": "video", "path": str(self.root / "source.txt"), "sha256": sha(self.root / "source.txt"), "duration": 60}
        write(self.root / "sources.json", [src])
        write(self.root / "run.json", {"scope": [0, 60], "video": "video", "language": "en",
              "agreement": {"response": "Approved synthetic fixture", "type": "lecture", "sections": ["Method"]}, "operations": {}})
        (self.root / "content/topics").mkdir(parents=True)
        (self.root / "publication").mkdir()
        (self.root / "content/topics/method.md").write_text(
            "# Method\n<!-- block:method -->\nAn explanation. [Source](source:video#t=0)\n"
            "<!-- block:limit -->\nA limitation from later. [Source](source:video#t=45)\n", encoding="utf-8")
        (self.root / "publication/reading.md").write_text(
            "# Method\n<!-- block:method -->\nAn explanation. [Source](source:video#t=0)\n"
            "<!-- block:limit -->\nThe later qualification. [Source](source:video#t=45)\n", encoding="utf-8")
        write(self.root / "content/manifest.json", {"schema_version": 1, "language": "en", "title": "Method",
              "manuscript": "publication/reading.md", "evidence": [], "limitations": "", "topics": [{"id": "method",
              "title": "Method", "summary": "Explanation and limitation", "path": "content/topics/method.md",
              "blocks": [{"id": "method", "sources": [{"source": "video", "start": 0, "end": 45}]},
                         {"id": "limit", "sources": [{"source": "video", "start": 45, "end": 60}]}]}]})
        write(self.root / "review/coverage.json", [{"start": 0, "end": 60, "kind": "content", "blocks": ["method", "limit"]}])

    def test_valid_cross_episode_topic(self):
        self.assertTrue(validate(self.root)["passed"])

    def test_missing_late_qualification_blocks_publication(self):
        p = self.root / "publication/reading.md"
        p.write_text("<!-- block:method -->\nOnly the explanation.", encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_source_change_is_not_silently_accepted(self):
        (self.root / "source.txt").write_text("Changed recording", encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_coverage_hole_is_an_error(self):
        write(self.root / "review/coverage.json", [{"start": 5, "end": 60, "kind": "content", "blocks": ["method"]}])
        self.assertFalse(validate(self.root)["passed"])

    def test_explicit_gap_needs_visible_limitation(self):
        write(self.root / "review/coverage.json", [{"start": 0, "end": 60, "kind": "gap", "note": "Unclear audio"}])
        self.assertFalse(validate(self.root)["passed"])
        data = read(self.root / "content/manifest.json")
        data["limitations"] = "The passage could not be resolved."
        write(self.root / "content/manifest.json", data)
        self.assertTrue(validate(self.root)["passed"])

    def test_reference_outside_recording_is_an_error(self):
        data = read(self.root / "content/manifest.json")
        data["topics"][0]["blocks"][0]["sources"][0]["end"] = 100
        write(self.root / "content/manifest.json", data)
        self.assertFalse(validate(self.root)["passed"])

    def test_visible_time_link_must_also_be_valid(self):
        p = self.root / "content/topics/method.md"
        p.write_text(p.read_text().replace("#t=45", "#t=450"), encoding="utf-8")
        self.assertFalse(validate(self.root)["passed"])

    def test_negative_page_locator_is_an_error(self):
        data = read(self.root / "content/manifest.json")
        data["topics"][0]["blocks"][0]["sources"] = [{"source": "video", "locator": {"page": -1}}]
        write(self.root / "content/manifest.json", data)
        self.assertFalse(validate(self.root)["passed"])

    def test_optional_correction_invalidates_content_revision(self):
        before = validate(self.root)["content_revision"]
        write(self.root / "review/corrections.json", [{"target": "method", "text": "Corrected", "origin": "user"}])
        self.assertNotEqual(before, validate(self.root)["content_revision"])

    def test_local_image_is_a_content_dependency(self):
        image = self.root / "diagram.png"
        image.write_bytes(b"one")
        path = self.root / "publication/reading.md"
        path.write_text(path.read_text() + "\n![Diagram](../diagram.png)", encoding="utf-8")
        before = validate(self.root)["content_revision"]
        image.write_bytes(b"two")
        self.assertNotEqual(before, validate(self.root)["content_revision"])

    def test_work_paths_cannot_escape_run(self):
        with self.assertRaises(ValueError):
            inside(self.root, "../elsewhere")

    def test_cache_reuses_only_unchanged_outputs(self):
        calls = []
        output = self.root / "artifact.txt"
        def action():
            calls.append(1)
            output.write_text("result")
            return [output]
        first = operation(self.root, "test", {"video": sha(self.root / "source.txt")}, {}, action)
        second = operation(self.root, "test", {"video": sha(self.root / "source.txt")}, {}, action)
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        output.write_text("incomplete")
        self.assertEqual(status(self.root)["operations"]["test"], "stale")
        operation(self.root, "test", {"video": sha(self.root / "source.txt")}, {}, action)
        self.assertEqual(len(calls), 2)

    def test_failed_operation_can_resume(self):
        def fail():
            raise RuntimeError("Interrupted")
        with self.assertRaises(RuntimeError):
            operation(self.root, "test", {}, {}, fail)
        self.assertEqual(read(self.root / "run.json")["operations"]["test"]["state"], "blocked")
        file = self.root / "success.txt"
        file.write_text("resumed")
        operation(self.root, "test", {}, {}, lambda: [file])
        self.assertEqual(status(self.root)["operations"]["test"], "completed")

    def test_visual_review_is_bound_to_pdf_hash(self):
        pdf = self.root / "output/digest.pdf"
        pdf.parent.mkdir()
        pdf.write_bytes(b"%PDF-synthetic-v1")
        link_report = self.root / "output/links.json"
        write(link_report, {"passed": True, "files": [], "pdf": {"passed": True, "sha256": sha(pdf)}})
        content_revision = validate(self.root)["content_revision"]
        write(self.root / "output/build.json", {"content_revision": content_revision, "files": {"output/digest.pdf": sha(pdf), "output/links.json": sha(link_report)}})
        run = read(self.root / "run.json")
        run["operations"]["publication"] = {"state": "completed"}
        write(self.root / "run.json", run)
        review(self.root, "content", "Synthetic check")
        review(self.root, "visual", "Synthetic check")
        self.assertEqual(release(self.root)["state"], "ready")
        pdf.write_bytes(b"%PDF-synthetic-v2")
        write(self.root / "output/build.json", {"content_revision": content_revision, "files": {"output/digest.pdf": sha(pdf), "output/links.json": sha(link_report)}})
        self.assertEqual(release(self.root)["state"], "draft")

    def test_failed_rebuild_does_not_release_previous_pdf(self):
        run = read(self.root / "run.json")
        run["operations"]["publication"] = {"state": "blocked"}
        write(self.root / "run.json", run)
        result = release(self.root)
        self.assertEqual(result["state"], "draft")
        self.assertIn("The last publication operation did not complete", result["errors"])


class TimeMappingCase(unittest.TestCase):
    def test_segment_only_provider_does_not_invent_word_times(self):
        result = normalize([{"offset": 100, "keep": [100, 110], "raw": "raw.json", "segments": [
            {"id": 0, "start": 1, "end": 4, "text": "A phrase", "words": None}]}], "video", 100, 110)
        self.assertEqual(result[0]["start"], 101)
        self.assertNotIn("words", result[0])

    def test_nonzero_offset_and_overlap_keep_each_word_once(self):
        parts = [
            {"offset": 100, "keep": [100, 105], "raw": "a.json", "segments": [{"id": 0, "text": "one two", "words": [
                {"start": 1, "end": 2, "word": " one"}, {"start": 5, "end": 6, "word": " two"}]}]},
            {"offset": 104, "keep": [105, 110], "raw": "b.json", "segments": [{"id": 0, "text": "two", "words": [
                {"start": 1, "end": 2, "word": " two"}]}]}
        ]
        result = normalize(parts, "video", 100, 110)
        self.assertEqual([s["text"] for s in result], ["one", "two"])
        self.assertEqual([s["start"] for s in result], [101, 105])


@unittest.skipUnless(importlib.util.find_spec("docx") and importlib.util.find_spec("pptx"), "optional document readers unavailable")
class DocumentsCase(unittest.TestCase):
    def test_word_and_powerpoint_preserve_locators_and_notes(self):
        from documents import extract
        from docx import Document
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / "run.json", {"operations": {}})
            doc = Document()
            doc.add_heading("Method", 1)
            doc.add_paragraph("A condition that matters.")
            table = doc.add_table(rows=1, cols=2)
            table.cell(0, 0).text = "threshold"
            table.cell(0, 1).text = "0.3"
            doc.save(root / "notes.docx")
            deck = Presentation()
            slide = deck.slides.add_slide(deck.slide_layouts[1])
            slide.shapes.title.text = "Example"
            slide.placeholders[1].text = "Preserve the limitation"
            slide.notes_slide.notes_text_frame.text = "Speaker notes are not speech evidence."
            deck.save(root / "slides.pptx")
            for key, filename in [("notes", "notes.docx"), ("slides", "slides.pptx")]:
                register(root, key, root / filename)
                result = extract(root, key)
                records = read(root / result["files"][-1])["records"]
                self.assertTrue(records)
                if key == "notes":
                    self.assertTrue(any(r["kind"] == "table" and "0.3" in r["text"] for r in records))
                else:
                    self.assertTrue(any(r["kind"] == "notes" and r["locator"]["slide"] == 1 for r in records))
                self.assertTrue(extract(root, key)["cached"])


if __name__ == "__main__":
    unittest.main()
