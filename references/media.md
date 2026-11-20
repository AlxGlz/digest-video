# Speech, frames, and source time

## Audio and ASR

```sh
python /skill/scripts/digest.py --work /run audio
python /skill/scripts/digest.py --work /run transcribe --model /models/faster-whisper-small --language ru
```

The ASR language describes the speech, not the output language. The helper uses CPU int8, beam 5, temperature 0, no previous-text conditioning, word timestamps, and no VAD by default. These are a reproducible starting configuration, not an accuracy guarantee or a universal model recommendation. Select a stronger or environment-appropriate model when the material requires it.

The default ASR ownership windows are 300 seconds with four seconds of overlap. Raw responses remain in per-attempt files. Words are assigned to a window by their midpoint; normalized times are shifted to the original recording once. Check every join for lost/repeated words and incomplete explanations. Change chunk size to fit the environment, retaining neighboring context for content review.

Use `--start`, `--end`, `--chunk`, `--overlap`, and `--threads` for a selected passage. `--vad` creates a separate configuration, not a silent replacement of the baseline. Preserve the original audio. Faster-whisper's internal VAD maps timestamps back to input audio; if a different pipeline physically removes silence, preserve an explicit map to original time.

A second pass can help with a concrete suspect passage. Two Whisper-based engines agreeing is not independent confirmation. VAD may improve one passage while another disappears; silence confidence is not proof that a quiet question is irrelevant. If a model hallucinates, repeats, or returns no usable speech, inspect the source interval and try a justified alternative. Keep unresolved content visible with time references.

For another ASR tool, store the raw response and normalized JSONL using files.md. An approximate clip locator is acceptable when clearly labeled. Speaker diarization is optional; use neutral speaker labels unless identities are evidenced. Recheck source numbers, negations, function names, and technical terms against relevant materials and available audio understanding.

## Video evidence

```sh
python /skill/scripts/digest.py --work /run frame --at 3510
```

The frame helper preserves a full-resolution PNG, a readable copy, FFmpeg's source PTS, and a log. Seek using source time; retain the reported PTS instead of labeling the image with the requested seek time. For VFR or an unexpected timestamp origin, inspect the actual reported time and frame; do not derive a timestamp as frame_index / nominal_fps.

Use time-spaced overview frames plus detected-change candidates and targeted frames prompted by the explanation. Select a screen region when useful. No fixed scene threshold is a completeness test: a changed line of code or pointer position may matter without a scene cut. For a demonstration, capture the relevant before/after state or result. For a static slide, compare with the attachment before substituting its clearer rendering.

Keep the original and reading-size image. A contact sheet helps navigate; inspect the full relevant image before claiming that small code or table cells are readable. The final PDF should contain only images that support a particular explanation, with captions and source locations.
