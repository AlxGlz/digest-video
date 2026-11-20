# Reviewing evidence and writing content

## Episodes and coverage

Review every part of the agreed scope in manageable passages, with enough adjacent context to finish sentences and demonstrations. Save episode notes in `review/` with source locations. They must retain the explanation, example, important result, qualification, questions/answers, and screen actions. Condense repetition without losing the original reasoning.

Use `review/coverage.json` to account for intervals as content, repeated material linked to a content block, silence/technical pauses, or unresolved gaps. A filled coverage file checks the review process, not semantic completeness. Sampled overview frames and ASR segments alone cannot prove that all meaningful actions were captured.

For significant details, check source evidence even if the ASR sounds fluent. Investigate unclear terminology, numbers, negations, code edits, apparent topic jumps, and chunk boundaries. Prefer targeted evidence over rereading all files into context. Reprocess a suspect passage when changing model/context/settings offers a concrete benefit. If nothing further can resolve it, retain the known part, identify the gap, and cite its location in both deliverables.

Human proofreading is optional. A user correction is stored separately with its provenance and target interval/segment; the raw ASR remains unchanged. Do not complete a truncated correction by guessing. A correction supplied in text or a document is sufficient; no browser form or JSON download is required.

## Topics shared by the outputs

First form a topic map across the full scope. Merge explanations and later caveats even when they are far apart. For each topic, write a self-contained account that an agent can use after reading only the index and this file. The audience and detail level come from the recording. Preserve exact code identifiers and the speaker's terminology; retain original technical terms at first translated use when useful.

Each substantive content block needs source references and a stable ID. A block can hold an explanation plus its worked example; do not force one fact per record. Include limitations and distinctions between proposals, accepted decisions, and open questions. Avoid adding textbook material merely because it is related to the subject.

If a speaker fully works through two examples and assigns a third as optional reading, explain the first two and link the third where the recommendation belongs. If a demonstration depends on a code change or cursor location, attach evidence of that actual action. A slide rendering can replace a static screen image after matching it to the recording.

Common topics are publishable Markdown, with working notes kept separately. The PDF manuscript draws on the same blocks and sources, using connected prose, useful transitions, and nearby illustrations. It may reorganize the narrative; it must not introduce unsupported conclusions or lose caveats.

## Content review

Check the shared topics and PDF manuscript against the original evidence for significant examples, conditions, numbers, negations, attribution, and missing parts. Source-marker checks are only structural. Check important facts in the actual text, not merely that matching IDs occur in two files.

Try narrow questions that exercise the intended use: explaining a method, reconstructing a worked example, naming a condition under which it fails, or tracing a meeting's final decision to its reasons. Include an answer based on two separated episodes. Start from the index; record which topics were needed and whether their source locations verify the answer. Report actual token usage only if measured by the host; file size is not a token measurement.

Use optional delegation only if the environment and user permit it. A solo agent follows the same review. Developer self-checks do not count as independent fresh-session evaluations.
