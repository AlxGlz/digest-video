"""Regression checks for rendered citations, worker bounds, and resumable evidence."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import read, sha, write
from markdown_links import block_links, links, parsed_links, replace_links
from speech import budget, reusable, token_words, windows
import test_workflow


class CitationCase(unittest.TestCase):
    setUp = test_workflow.RunCase.setUp

    def test_manifest_bootstrap_preserves_existing_metadata(self):
        from manifest import prepare
        path = self.root / "content/manifest.json"
        previous = path.read_bytes()
        with self.assertRaises(ValueError):
            prepare(self.root, "New title")
        self.assertEqual(path.read_bytes(), previous)
        path.unlink()
        prepare(self.root, "New title")
        data = read(path)
        self.assertEqual(data["topics"][0]["blocks"][1]["sources"][0]["start"], 45)
        self.assertEqual(data["evidence"], [])

    def test_manifest_rejects_literal_citations(self):
        from manifest import prepare
        (self.root / "content/manifest.json").unlink()
        path = self.root / "content/topics/method.md"
        path.write_text("# Method\n<!-- block:method -->\n`[source](source:video#t=0)`", encoding="utf-8")
        with self.assertRaises(ValueError):
            prepare(self.root, "Title")
    def test_code_citations_do_not_satisfy_either_output(self):
        from publication import validate
        for name in ("content/topics/method.md", "publication/reading.md"):
            path = self.root / name
            before = path.read_text(encoding="utf-8")
            for prefix, suffix in (("`", "`"), ("\n```md\n", "\n```\n"), ("\n    ", "\n")):
                path.write_text(before.replace("[Source](source:video#t=0)", prefix+"[Source](source:video#t=0)"+suffix), encoding="utf-8")
                report = validate(self.root)
                self.assertFalse(report["passed"], (name, prefix))
                self.assertTrue(any("needs a rendered source link" in e for e in report["errors"]))
            path.write_text(before, encoding="utf-8")

    def test_export_preserves_literal_markdown_examples(self):
        value = "`[example](source:video#t=999)` and [real](source:video#t=1)"
        changed = replace_links(value, lambda m: "[exported](file:///clip#t=1)")
        self.assertIn("`[example](source:video#t=999)`", changed)
        self.assertEqual(len(list(links(changed))), 1)

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc not installed")
    def test_real_parser_excludes_backticks_and_preserves_block_association(self):
        path = self.root / "sample.md"
        path.write_text("<!-- block:a -->\n[valid](source:video#t=1)\n\n<!-- block:b -->\n`[fake](source:video#t=2)`\n", encoding="utf-8")
        found, blocks = parsed_links(path, "pandoc", self.root / "parser.log")
        self.assertEqual(found, ["source:video#t=1"])
        self.assertEqual(blocks, {"a": ["source:video#t=1"], "b": []})


class ParallelCase(unittest.TestCase):
    def test_workers_share_total_budget(self):
        self.assertEqual(budget(2, 2)["threads_per_worker"], 1)
        self.assertEqual(budget(2, 1)["threads_per_worker"], 2)
        with self.assertRaises(ValueError):
            budget(2, 3)

    def test_windows_preserve_nonzero_origin_and_final_short_window(self):
        parts = windows(101, 232, 60, 4)
        self.assertEqual([p["keep"] for p in parts], [[101,161],[161,221],[221,232]])
        self.assertEqual([p["offset"] for p in parts], [101,159,219])
        self.assertEqual(parts[-1]["end"], 232)
        for chunk, overlap in ((0,0),(5,5),(5,-1)):
            with self.assertRaises(ValueError):
                windows(0,20,chunk,overlap)

    def test_vad_offset_added_before_window_offset(self):
        from media import normalize
        words = token_words(["▁first", "▁sec", "ond"], [1,2,2.3], 10,14)
        part = {"offset": 100, "keep": [100,120], "raw": "raw.json", "segments": [
            {"id": 0, "text": "first second", "words": words}]}
        result = normalize([part], "video", 100,120)
        self.assertEqual(result[0]["start"], 111)
        self.assertEqual(result[0]["text"], "first second")
        self.assertEqual(result[0]["words"][-1]["end"],114)

    def test_interrupted_or_changed_window_is_not_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "part.json"
            task = {"raw": str(raw), "signature": "a"}
            self.assertFalse(reusable(task))
            write(raw, {"signature": "a", "segments": []})
            self.assertFalse(reusable(task))
            write(Path(str(raw)+".sha256.json"), {"sha256": sha(raw), "signature": "a"})
            self.assertTrue(reusable(task))
            self.assertFalse(reusable(dict(task, signature="b")))
            write(raw, {"signature": "a", "segments": ["changed"]})
            self.assertFalse(reusable(task))


if __name__ == "__main__":
    unittest.main()
