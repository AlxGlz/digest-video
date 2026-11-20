# Publishing and checking both outputs

With the files described in files.md prepared:

```sh
python /skill/scripts/digest.py --work /run check
python /skill/scripts/digest.py --work /run build --font Arial --size 11
python /skill/scripts/digest.py --work /run render
```

Supply `--pandoc` and `--typst` executable paths if they are not on PATH. Choose an installed font with glyph coverage for the output language; Arial is a tested Cyrillic option on Windows, not a guaranteed font on every host. Configure other typography in the saved manuscript metadata or adapt the rendering step if the environment requires it.

The build exports topics and an index, writes an intermediate `output/reading.md`, invokes Pandoc to create `output/digest.typ`, then invokes Typst separately to produce `output/digest.pdf`. All copied images remain under `output/`, avoiding absolute-drive image paths in the Typst source. `output/build.json` records the input revision, formatting, and generated file hashes. The editable authoritative narrative remains `publication/reading.md`.

`check` validates source availability/hashes, actual confirmation being recorded, output language, block coverage in both sources, source references, local files, time intervals, and coverage holes. It does not evaluate prose, source truth, word alignment, or legibility. Fix technical failures before proceeding, while retaining evidence of unresolved content.

Review the content using authoring.md. Then inspect every rendered PDF page: check glyphs, readable captions/images/code/tables, clipping, page breaks, links, and whether each figure sits usefully near its explanation. Open individual pages at a readable size. A contact sheet is useful for navigation, but does not replace checking small details.

Record only checks actually performed:

```sh
python /skill/scripts/digest.py --work /run review content --note "Describe the source checks and retrieval questions actually checked."
python /skill/scripts/digest.py --work /run review visual --note "Describe the rendered pages actually inspected and any remaining limitations."
python /skill/scripts/digest.py --work /run release
```

The `review` command stores your statement; it is not an automated reviewer. `release` requires a current successful build, unchanged generated files, current content review, and visual review of this PDF. If the environment cannot complete a required review, keep the release as a draft and explain the missing verification. A clearly stated source ambiguity can remain in a finished digest; an unperformed required check cannot be reported as passed.

For a format-only change, rerun `build` with the requested formatting and inspect a fresh rendering. The content review can remain valid if the underlying content is unchanged; the visual review must refer to the new PDF. Keep source evidence and authoring files unchanged. Record actual measured token use only when the host provides it.

Deliver `output/digest.pdf` and `output/index.md`. The topics and assets form the Markdown bundle. Cite significant limits near the affected text and briefly in the delivery message. Do not present a bounded test excerpt as a digest of the full recording.
