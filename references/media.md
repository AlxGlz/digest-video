# Speech, frames, and source time

## Select and measure ASR

Inspect hardware, packages, model caches and language support. Keep weights and virtual environments in a reusable user cache outside the skill and deliverables. `doctor` reports `DIGEST_VIDEO_CACHE` or, by default, `~/.cache/digest-video`, with an optional `venv` interpreter and `models/` directories. Inspect these before installing or downloading. Reuse verified models and tools, never another recording's transcript. The local path needs no account or paid service.

Before a long run, measure a 1-3 minute representative pilot containing terminology, numbers, and, if available, a quiet audience question. Listen when the environment supports audio; cross-check visible source material and suspect passages with a stronger recognizer. Choose the fastest configuration that preserves meaning, conditions, negations, and important names. Save the choice, measured time and quality limitations in `review/asr-choice.md`. Fluent output, automatic confidence, or agreement between related models is not proof of accuracy.

For Russian CPU audio, test the small int8 [Sherpa ONNX Zipformer model](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/zipformer-transducer-models.html) alongside a suitable Whisper model. The tested archive is [sherpa-onnx-zipformer-ru-int8-2025-04-20](https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-ru-int8-2025-04-20.tar.bz2). Check upstream license and intended language; weights are not bundled. Install `scripts/requirements-asr.txt` and, for Zipformer, `scripts/requirements-zipformer.txt`. The model folder needs encoder, decoder, joiner ONNX files and tokens.txt. The helper prefers int8 files and rejects ambiguous filenames.

```sh
python /skill/scripts/digest.py --work /run transcribe --engine zipformer --model /cache/zipformer-ru --language ru --start 120 --end 240 --cpu-budget 2
python /skill/scripts/digest.py --work /run transcribe --engine whisper --model /cache/faster-whisper-large-v3-turbo --language ru --start 120 --end 240 --cpu-budget 2 --batch-size 4 --vad
```

The speech language may differ from the output language. Zipformer language support comes from its model; `--language` records the choice, not a language switch. Use Whisper or another suitable model for unsupported languages or substantial code switching. Whisper uses CPU int8, beam 5, temperature 0, no previous-text conditioning, and word timestamps. A nonzero batch size requires explicit `--vad`; ordinary Whisper has VAD off unless requested. Zipformer uses greedy decoding and explicit Silero VAD, adding VAD cut offsets to token estimates. Raw files record effective settings, model hashes, versions and timings.

## Bounded parallelism and resumption

Start with `--cpu-budget 2 --jobs 1`. Compare `--cpu-budget 2 --jobs 2` on the same pilot with multiple ownership windows, for example `--chunk 60`. Total configured inference threads are `jobs * floor(cpu-budget / jobs)`; `--threads` aliases the total budget. This leaves practical headroom on a multicore PC, but is not a hard percentage CPU cap: VAD, imports, OS scheduling, memory and I/O also consume resources. Do not run several full-budget ASR commands concurrently. Each process loads its own model; start large Whisper with one worker and a modest batch. More workers or threads can be slower. See [CTranslate2 parallelism](https://opennmt.net/CTranslate2/parallel.html) and [faster-whisper benchmarks](https://github.com/SYSTRAN/faster-whisper#benchmark).

The coordinator extracts mono 16 kHz audio once per requested range, then workers read overlapping windows from that WAV. FFmpeg and numerical-library thread settings are bounded too. Only the coordinator updates run.json. Workers save separate raw files. Successful windows resume only when settings/source/model signatures and stored output hashes match. Changed or incomplete windows are recomputed. Keep one coordinator per run directory.

Default ownership windows are 300 seconds with four seconds total overlap. `--chunk` and `--overlap` change them. Words belong to the window containing their midpoint; original-recording time is added once. Keep raw overlaps and inspect joins for lost/repeated words, especially explanations and quiet questions. Different overlapping recognitions can disagree; midpoint ownership is not semantic deduplication. Never delete silence without preserving its time map.

Progress goes to stderr after each completed window. The result lists `segments.jsonl` and `index.json`. The index records total wall time, audio preparation, worker phase, reused windows, and a rough full-scope extrapolation. Raw parts record worker load and decode time. Load time repeats for the same PID: count it once per worker. Do not sum concurrent decode times as elapsed time. Pilot estimates include setup; content, VAD, caches and CPU contention affect speed. Qualify the estimate.

Human ASR proofreading is optional. Use stronger targeted passes for concrete uncertainties; preserve raw evidence and correction provenance. If the source cannot resolve a detail, retain the known part with a timed gap. Another engine is valid if it emits the files.md evidence contract and records effective settings and original-time mapping. Diarization is optional; do not guess identities.

## Video evidence

```sh
python /skill/scripts/digest.py --work /run frame --at 3510
```

The frame helper preserves a full-resolution PNG, a readable copy, FFmpeg's source PTS, and a log. Seek using source time; retain the reported PTS instead of labeling the image with the requested seek time. For VFR or an unexpected timestamp origin, inspect the actual reported time and frame; do not derive a timestamp as frame_index / nominal_fps.

Use time-spaced overview frames plus detected-change candidates and targeted frames prompted by the explanation. Select a screen region when useful. No fixed scene threshold is a completeness test: a changed line of code or pointer position may matter without a scene cut. For a demonstration, capture the relevant before/after state or result. For a static slide, compare with the attachment before substituting its clearer rendering.

Keep the original and reading-size image. A contact sheet helps navigate; inspect the full relevant image before claiming that small code or table cells are readable. The final PDF should contain only images that support a particular explanation, with captions and source locations.
