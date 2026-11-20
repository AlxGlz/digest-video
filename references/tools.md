# Tools and setup

Use existing capabilities first. This package's helpers run on Python 3.11+; the coordinator and validation use the standard library. Install optional dependencies only for a selected branch, in an isolated environment outside the skill directory. Use the target shell's quoting and the actual paths supplied by the user.

Examples below use `python` for the selected interpreter. Replace `/skill` and `/run` with actual paths; quote paths containing spaces. `--work` precedes the subcommand.

```sh
python /skill/scripts/digest.py doctor
python /skill/scripts/digest.py --work /run init --video /input/recording.mp4 --language ru
python /skill/scripts/digest.py --work /run source slides /input/slides.pptx
python /skill/scripts/digest.py --work /run status
```

For a user-requested excerpt, `init --start SECONDS --end SECONDS` retains original-recording time. The default is the entire recording. `source ID PATH` also refreshes a changed source revision or relocates an unchanged source. Check the scope after replacing a recording.

The preferred local branches:

| Operation | Tools | Notes |
| --- | --- | --- |
| Audio, metadata, frames | FFmpeg / ffprobe | Accept executable paths through `--ffmpeg` / `--ffprobe`; do not infer time from frame number. |
| Local ASR | faster-whisper; Sherpa ONNX Zipformer for supported languages | CPU helpers, bounded workers, pilot before full run; see media.md. Existing models, no automatic weight download. |
| Alternative ASR | whisper.cpp, suitable native tool, optionally remote service | Normalize results using files.md; verify timestamp units and supported fields. |
| PDF text and rendering | pypdf, pypdfium2, Pillow | Page locators; visual inspection still necessary. |
| DOCX / PPTX reading | Native document tools, python-docx / python-pptx, MarkItDown | Reading and rendering have different capabilities. See attachments.md. |
| Office rendering | Available office tool or LibreOffice | Save a derivative with conversion provenance; no need to produce Office deliverables. |
| Scans | Available OCR / Tesseract / OCRmyPDF | Inspect significant numbers, symbols, and tables against images. |
| PDF publication | Pandoc then Typst | Two explicit commands, relative local images, Unicode font installed on the host. |

Optional dependency files are in `scripts/requirements-*.txt`. They record tested versions, not a requirement to replace working environment tools. For example:

```sh
python -m venv /tools/digest-venv
/tools/digest-venv/bin/python -m pip install -r /skill/scripts/requirements-documents.txt
```

On Windows use the environment's `Scripts/python.exe`. `uv pip install --python PATH -r FILE` is also suitable. FFmpeg, Pandoc, Typst, office applications, OCR engines, and model weights are separate dependencies. Respect the environment's permissions and already-given authorization when installing or downloading.

The tested faster-whisper combination pins PyAV 18.1.0: PyAV 19 removed an argument used by the tested faster-whisper release. Verify the actual environment rather than broadly upgrading dependencies. A model directory must contain compatible CTranslate2 weights/tokenizer files; keep its source, revision, and license with the download record. The helper hashes local model files and records package versions.

Use local ASR by default. A suitable environment-provided or remote tool is allowed by the workflow when authorized in the current environment. Check its current audio/time/speaker contract before use; a plain transcript can only inherit the known clip interval, not invented word timestamps. Local execution after downloads does not establish a fully air-gapped installation.

Do not bundle third-party binaries, model weights, or private documents into the skill repository. Follow their licenses when acquiring or redistributing them.
