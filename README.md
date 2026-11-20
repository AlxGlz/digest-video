# digest-video

A portable agent skill that turns a local lecture, seminar, meeting, or mixed-format recording into a detailed illustrated PDF and source-linked topical Markdown. Supporting materials can include slides, Word documents, PDFs, code, or other files read through available environment tools.

The skill's instructions are in English. Conversation and deliverables follow the user's language. A single agent can run the workflow using local tools.

## Use

Place this repository's `digest-video` folder in a skill directory recognized by your agent, or explicitly ask it to read [SKILL.md](SKILL.md). Provide the local recording path and any attachments. The agent inspects representative material, proposes the recording type and structure, and waits for your confirmation before authoring the digest. Human transcript proofreading is optional.

Start with the agent's existing tools. Optional Python helpers and dependencies are described in [references/tools.md](references/tools.md). Run `python scripts/digest.py --help` to inspect commands. Keep working data outside this repository. Helper dependencies, model weights, FFmpeg, Pandoc, and Typst are installed separately when needed.

## Capabilities and verification

The skill includes local Whisper and Zipformer adapters with measured pilots, bounded CPU workers and resumable windows; document reading; rendered Markdown link checks; and a reusable Pandoc/Typst reading profile. Authoring guidance preserves the narrative, distinguishes audience discussion, and plans images by explanatory value. The agent still performs semantic authoring, evidence review, and visual inspection. This is not a standalone automatic video summarizer.

Readability, factual completeness and visual quality need separate review; helper tests do not establish accuracy on arbitrary recordings.

Tests: `python -m unittest discover -s tests -v`. Document-reader tests use the optional document dependencies; all test inputs are synthetic.
