# Working files and provenance

Keep the run outside the skill checkout. UTF-8 text and relative paths within the run allow another agent to resume. The examples use seconds in the original recording and English field names; authored text remains in the user's language.

After authoring marked `content/topics/*.md` with real inline `source:` citations, `digest.py --work /run prepare-manifest --title "Digest title"` can generate initial manifest metadata. It never overwrites an existing manifest and does not write the narrative or claim a review. Review topic order, replace title-only summaries with useful retrieval summaries, expand cited time points into supported intervals when appropriate, and add evidence paths and limitations. Then author the PDF manuscript and coverage map. This removes mechanical ID/link transcription while leaving editorial decisions explicit.

`run.json` stores the recording source ID, agreed time scope, output language, actual structure confirmation, and cached operations. `sources.json` stores source IDs, paths, hashes, roles, media metadata, and prior revisions. Register every attachment. Relocate an unchanged source by ID; a changed hash invalidates dependent work. Keep the old original separately if it must remain available.

After receiving the user's structure response, save an agreement JSON and import it with `digest.py --work /run agreement /run/agreement.json`:

```json
{
  "type": "mixed",
  "sections": ["Concepts and examples", "Practical investigation", "Qualifications and answers"],
  "response": "The actual response confirming or correcting these sections"
}
```

The example response is a description of the required value, not user authorization. The script stores the response; it cannot verify that a conversation occurred.

## Evidence and review

Raw tool responses stay in `evidence/`. ASR normalization uses JSONL records with `id`, `source`, `start`, `end`, `text`, `timing`, and a path to the raw response. Optional `words` and speaker labels must come from a suitable source. Timing values are global seconds; document the clip offset and any time mapping. `timing` distinguishes engine estimates, approximate clip intervals, and any actually reviewed timing.

Attachment records contain `source`, `locator`, `kind`, and `text` or an image path. Locators may describe a PDF page, slide, paragraph, table/cell, or code line. Keep extracted-image locations and their relationship to the original. Record source hashes, tool versions, conversion lineage, and extraction limitations in the accompanying index. For other readers, preserve their raw response and equivalent records rather than forcing a lossy text-only export.

Save episode explanations in `review/episodes.md` or several small Markdown files. Save optional corrections in `review/corrections.json`, with target, previous version, corrected text, origin, supporting evidence, and status. User corrections, attachment spelling fixes, and agent hypotheses must remain distinguishable.

`review/coverage.json` accounts for the agreed scope. For example:

```json
[
  {"start": 0, "end": 40, "kind": "content", "blocks": ["method"]},
  {"start": 40, "end": 45, "kind": "silence", "note": "Technical pause"},
  {"start": 45, "end": 60, "kind": "content", "blocks": ["limitation"]}
]
```

Kinds are `content`, `repeat`, `silence`, and `gap`. Content and repeats link to existing blocks. A gap needs a reason and visible limitations in the outputs. Overlaps are allowed; unexplained holes are errors. Use the true run scope, not these illustrative times.

## Publishable content

Write topics in `content/topics/` and the narrative in `publication/reading.md`. Authoring source references use inline links such as `[recording, 00:00:12](source:video#t=12)` or `[slides.pdf, page 4](source:slides#page=4)` for a PDF attachment. Export keeps these as working local links in Markdown and plain visible labels in the final PDF; see publishing.md. Do not use a PDF page fragment for a PPTX viewer unless it supports it: the visible slide/paragraph locator still makes the reference usable.

Local image paths are relative to the Markdown file, for example `../../evidence/pages/HASH/page-0004.png`. Use inline Markdown links, enclosing targets with spaces in angle brackets; the exporter does not support reference-style link definitions. Keep original technical identifiers intact. Include descriptive captions with source locations.

Place `<!-- block:method -->` before the corresponding section in the topic and PDF manuscript. Each declared block appears once in each output's source. These markers establish coverage links; they do not prove that the two explanations are substantively equivalent. Human-readable source citations remain necessary.

`content/manifest.json`:

```json
{
  "schema_version": 1,
  "language": "en",
  "title": "Understanding the method",
  "manuscript": "publication/reading.md",
  "evidence": ["evidence/asr/RUN/segments.jsonl", "evidence/documents/slides/RUN/document.json"],
  "limitations": "",
  "topics": [
    {
      "id": "method",
      "title": "Method and its limits",
      "summary": "How it works, the example, and when it fails.",
      "path": "content/topics/method.md",
      "blocks": [
        {"id": "method", "sources": [{"source": "video", "start": 0, "end": 40}]},
        {"id": "limitation", "sources": [{"source": "video", "start": 45, "end": 60}, {"source": "slides", "locator": {"slide": 4}}]}
      ]
    }
  ]
}
```

Replace illustrative files and values with actual ones. Include the evidence files used to author the content so a changed normalized transcript invalidates the publication. The helper also fingerprints review files, source inventory, local linked assets, agreement, and content. `limitations` is visible text in the output language, included in the index and topics and near the start of the PDF; leave it empty only when no shared limitation needs to be communicated. Place local limitations with the affected explanation as well.

The manuscript can use Pandoc YAML metadata (`title`, `lang`) and ordinary Markdown, tables, fenced code, math, captions, and images. The exporter copies required local assets, rewrites internal links, preserves readable source citations, removes private block markers, and exports the topics directly. Working notes are not exported. Original videos and attachments remain external and may require relocation; source labels and visible time/page locators remain meaningful even when a viewer cannot seek using a link.

## State and revisions

`status` reports saved operation state and changed artifacts. An operation is reused only when its input signature and output hashes still match. Raw ASR and document attempts have separate paths. A changed source requires `source ID PATH`, followed by the affected extraction and authoring. Never substitute a new source under an old hash.

After a correction, update the affected episodes, topics, manuscript, and reviews. Scripts detect stale files; the agent performs semantic reconciliation. After a format-only change, run only `build`, `render`, visual review, and `release`. `checks/` distinguishes structural reports from agent content/visual review records, each tied to a content revision and, for visual review, a PDF hash.

Do not edit the same run concurrently from multiple agents. Split optional delegated work into separate files and let one coordinator merge it. Run state writes are atomic but are not a multiwriter database.
