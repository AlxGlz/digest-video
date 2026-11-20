# Reviewing evidence and writing content

## Episodes and coverage

Review every part of the agreed scope in manageable passages, with enough adjacent context to finish sentences and demonstrations. Save episode notes in `review/` with source locations. They must retain the explanation, example, important result, qualification, questions/answers, and screen actions. Condense repetition without losing the original reasoning.

For each meaningful episode, capture the motivating question, what the audience already knows, the explanation or action, a worked example and its result, qualifications, and why the next subject follows. Record its role: main explanation, demonstration, audience question, answer, or uncertain discussion. These are evidence-based review notes, not a chronology generated afterward from coverage IDs. No fixed length or mandatory form is needed.

Keep a compact illustration map beside these notes: the point an image explains, source/time/page, candidate image, and whether it is used or why omitted. Include important diagrams, tables, equations, changed code, and observed demo results. A useful caption explains what to notice. Inspect full images for readability; do not treat a contact sheet or a fixed number of images as sufficient coverage.

Use `review/coverage.json` to account for intervals as content, repeated material linked to a content block, silence/technical pauses, or unresolved gaps. A filled coverage file checks the review process, not semantic completeness. Sampled overview frames and ASR segments alone cannot prove that all meaningful actions were captured.

For significant details, check source evidence even if the ASR sounds fluent. Investigate unclear terminology, numbers, negations, code edits, apparent topic jumps, and chunk boundaries. Prefer targeted evidence over rereading all files into context. Reprocess a suspect passage when changing model/context/settings offers a concrete benefit. If nothing further can resolve it, retain the known part, identify the gap, and cite its location in both deliverables.

Human proofreading is optional. A user correction is stored separately with its provenance and target interval/segment; the raw ASR remains unchanged. Do not complete a truncated correction by guessing. A correction supplied in text or a document is sufficient; no browser form or JSON download is required.

## Topics shared by the outputs

First form a topic map across the full scope. Merge explanations and later caveats even when they are far apart. For each topic, write a self-contained account that an agent can use after reading only the index and this file. The audience and detail level come from the recording. Preserve exact code identifiers and the speaker's terminology; retain original technical terms at first translated use when useful.

Each substantive content block needs source references and a stable ID. A block can hold an explanation plus its worked example; do not force one fact per record. Include limitations and distinctions between proposals, accepted decisions, and open questions. Avoid adding textbook material merely because it is related to the subject.

If a speaker fully works through two examples and assigns a third as optional reading, explain the first two and link the third where the recommendation belongs. If a demonstration depends on a code change or cursor location, attach evidence of that actual action. A slide rendering can replace a static screen image after matching it to the recording.

Common topics are publishable Markdown, with working notes kept separately. The PDF manuscript draws on the same blocks and sources, using connected prose, useful transitions, and nearby illustrations. It may reorganize the narrative; it must not introduce unsupported conclusions or lose caveats.

Before composing the PDF, outline its chain of explanation. At each subsection transition, state the unresolved question or dependency that makes the next step relevant. For example, when a demonstration moves from a requirement to a test, explain what the test must establish before introducing the testing tool. Derive the connection from the source; if it is absent, acknowledge the change of subject instead of inventing the lecturer's reasoning. One transition at the start of a large chapter is insufficient when its subsections change purpose.

Keep each worked example complete: initial condition → intervention → observed result → explanation → scope or failure condition. A table of outcomes cannot replace why a particular outcome occurred. Reconcile later corrections across every relevant topic and PDF passage; also check summary tables and assignment instructions for stale values.

Integrate discussion with its topic but mark its origin. Use a short localized blockquote with bold labels such as **Audience question (paraphrased)** and **Lecturer's answer**, then resume the main explanation in normal prose. Label uncertain attribution **Discussion**. Do not turn paraphrases into verbatim quotations or infer speaker identity from ASR alone. A later answer may qualify an earlier statement without becoming an uninterrupted block of lecture text.

## Content review

Check the shared topics and PDF manuscript against the original evidence for significant examples, conditions, numbers, negations, attribution, and missing parts. Source-marker checks are only structural. Check important facts in the actual text, not merely that matching IDs occur in two files.

Perform a separate reader pass through the PDF manuscript. Name the subsection transitions and first tool introductions inspected, missing links in examples, Q&A attribution fixes, and important visual episodes represented. If an unfamiliar reader cannot explain why the next method appears, repair the passage before publishing. Preserve explanation instead of targeting an arbitrary page count. The Markdown topics remain independently understandable when the PDF uses a different order.

Try narrow questions that exercise the intended use: explaining a method, reconstructing a worked example, naming a condition under which it fails, or tracing a meeting's final decision to its reasons. Include an answer based on two separated episodes. Start from the index; record which topics were needed and whether their source locations verify the answer. Report actual token usage only if measured by the host; file size is not a token measurement.

Use optional delegation only if the environment and user permit it. A solo agent follows the same review. Describe reviews performed by the author as self-checks.
