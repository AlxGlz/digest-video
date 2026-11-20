# Publishing and checking both outputs

With the files described in files.md prepared:

```sh
python /skill/scripts/digest.py --work /run check
python /skill/scripts/digest.py --work /run build --font Arial --size 11
python /skill/scripts/digest.py --work /run render
```

Supply `--pandoc` and `--typst` executable paths if they are not on PATH. Choose an installed font with glyph coverage for the output language; Arial is a tested Cyrillic option on Windows, not a guaranteed font on every host. Configure other typography in the saved manuscript metadata or adapt the rendering step if the environment requires it.

The build exports topics and an index, writes an intermediate `output/reading.md`, invokes Pandoc to create `output/digest.typ`, then invokes Typst separately to produce `output/digest.pdf`. All copied images remain under `output/`, avoiding absolute-drive image paths in the Typst source. `output/build.json` records the input revision, formatting, and generated file hashes. The editable authoritative narrative remains `publication/reading.md`.

The bundled `assets/reading.typ`, `reading.yaml`, and `reading.lua` profile keeps figures at their narrative position, disables hyphenation, styles Q&A blockquotes and code, uses A4 margins, and keeps a short table with its immediately preceding heading and optional short introduction. Larger tables remain breakable. The files are included automatically and their hashes are part of the build settings. Avoid custom floating-figure rules that can override the profile and move an image into a sentence. Start with this profile before inventing a template. Split long tables into meaningful units with repeated headers; inspect their beginnings and page transitions. Oversized images/tables still need editorial resizing and visual review. Adapt a private copy when necessary and record custom build settings; do not modify the installed skill.

`check` validates source availability/hashes, actual confirmation being recorded, output language, block coverage in both sources, source references, local files, time intervals, and coverage holes. It does not evaluate prose, source truth, word alignment, or legibility. Fix technical failures before proceeding, while retaining evidence of unresolved content.

Every content block needs actual inline source links in both the topic and manuscript. Do not wrap a citation in backticks. Code examples remain literal and are excluded from citation checks and export rewriting. The build also parses input and exported Markdown with Pandoc, checking that links are real Link nodes; `output/links.json` records this check. Open representative exported source and index links to verify the viewer behavior. A file link with a time fragment is a locator even when the user's player does not seek automatically.

Review the content using authoring.md. Then inspect every rendered PDF page: check glyphs, readable captions/images/code/tables, clipping, page breaks, links, and whether each figure sits usefully near its explanation. Open individual pages at a readable size. A contact sheet is useful for navigation, but does not replace checking small details.

Inspect page pairs at every table, image and section boundary. Look for a stranded heading, a table beginning with one row, a sentence interrupted by a figure, excessive empty space, or a caption separated from its image. After a layout change, inspect the new pages and affected neighbors. A successful renderer does not establish good layout.

Record only checks actually performed:

```sh
python /skill/scripts/digest.py --work /run review content --note "Describe the source checks and retrieval questions actually checked."
python /skill/scripts/digest.py --work /run review visual --note "Describe the rendered pages actually inspected and any remaining limitations."
python /skill/scripts/digest.py --work /run release
```

The `review` command stores your statement; it is not an automated reviewer. `release` requires a current successful build, unchanged generated files, current content review, and visual review of this PDF. If the environment cannot complete a required review, keep the release as a draft and explain the missing verification. A clearly stated source ambiguity can remain in a finished digest; an unperformed required check cannot be reported as passed.

For a format-only change, rerun `build` with the requested formatting and inspect a fresh rendering. The content review can remain valid if the underlying content is unchanged; the visual review must refer to the new PDF. Keep source evidence and authoring files unchanged. Record actual measured token use only when the host provides it.

Deliver `output/digest.pdf` and `output/index.md`. The topics and assets form the Markdown bundle. Cite significant limits near the affected text and briefly in the delivery message. Do not present a bounded test excerpt as a digest of the full recording.
