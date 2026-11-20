"""Observable destinations in rendered PDFs, independently of Markdown syntax."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import read, write
from pdf_links import inspect_pdf
from publication import build, release, review
import test_workflow

TYPST = os.environ.get("DIGEST_VIDEO_TEST_TYPST") or shutil.which("typst")


class PdfPortabilityCase(unittest.TestCase):
    def test_pdf_actions_reject_file_relative_unc_drive_and_launch(self):
        from pypdf import PdfWriter
        from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
        for target in ("file:///C:/secret/recording.mp4#t=30", "../recording.mp4", "C:/video.mp4",
                       "\\\\host\\share\\video.mp4", "http://localhost:8000/video", "http://127.0.0.1/video"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temp:
                pdf = Path(temp) / "sample.pdf"
                writer = PdfWriter()
                page = writer.add_blank_page(width=200, height=200)
                page[NameObject("/Annots")] = ArrayObject([DictionaryObject({
                    NameObject("/Subtype"): NameObject("/Link"),
                    NameObject("/A"): DictionaryObject({NameObject("/S"): NameObject("/URI"),
                                                       NameObject("/URI"): TextStringObject(target)})})])
                writer.write(pdf)
                self.assertFalse(inspect_pdf(pdf)["passed"])
        for action in ("/Launch", "/GoToR"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temp:
                pdf = Path(temp) / "sample.pdf"
                writer = PdfWriter()
                page = writer.add_blank_page(width=200, height=200)
                page[NameObject("/Annots")] = ArrayObject([DictionaryObject({
                    NameObject("/A"): DictionaryObject({NameObject("/S"): NameObject(action)})})])
                writer.write(pdf)
                self.assertFalse(inspect_pdf(pdf)["passed"])


class PdfBuildCase(unittest.TestCase):
    setUp = test_workflow.RunCase.setUp

    @unittest.skipUnless(TYPST and shutil.which("pandoc"), "Pandoc and Typst required")
    def test_build_keeps_locators_images_web_and_navigation_without_local_pdf_links(self):
        from PIL import Image
        from pypdf import PdfReader
        image = self.root / "diagram.png"
        Image.new("RGB", (80, 40), (40, 110, 160)).save(image)
        path = self.root / "publication/reading.md"
        text = path.read_text(encoding="utf-8").replace("[Source](source:video#t=0)", "[Recording, 00:00:00](source:video#t=0)")
        text = text.replace("[Source](source:video#t=45)", "[Recording, 00:00:45](source:video#t=45)")
        text += '\n\n[Web](https://example.org/reference) [Back](#method)\n\n'
        text += '[Local](file:///C:/private/clip.mp4) [Topic](../content/topics/method.md)\n\n'
        text += '![Diagram](../diagram.png)\n'
        path.write_text(text, encoding="utf-8")
        build(self.root, typst=TYPST)
        report = read(self.root / "output/links.json")["pdf"]
        self.assertTrue(report["passed"])
        self.assertEqual([x["target"] for x in report["external_links"]], ["https://example.org/reference"])
        self.assertGreater(report["internal_links"], 0)
        pdf = PdfReader(self.root / "output/digest.pdf")
        self.assertIn("00:00:45", "".join(p.extract_text() for p in pdf.pages))
        self.assertGreater(sum(len(p.images) for p in pdf.pages), 0)
        self.assertIn("file:", (self.root / "output/topics/method.md").read_text(encoding="utf-8"))
        review(self.root, "content", "Synthetic source and locator check")
        review(self.root, "visual", "Synthetic fixture for release validation")
        self.assertEqual(release(self.root)["state"], "ready")
        link_report = read(self.root / "output/links.json")
        del link_report["pdf"]
        write(self.root / "output/links.json", link_report)
        self.assertEqual(release(self.root)["state"], "draft")


if __name__ == "__main__":
    unittest.main()
