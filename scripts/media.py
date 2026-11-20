"""Local media operations; time values always refer to the original recording."""
from pathlib import Path
import importlib.metadata
import re
import time
from dataclasses import asdict

from common import (dump_lines, execute, fingerprint, inside, interval, operation,
                    read, relative, sha, source, version, write)


def limits(root, start=None, end=None):
    run = read(Path(root) / "run.json")
    lo, hi = run["scope"]
    start = lo if start is None else start
    end = hi if end is None else end
    interval(start, end, lo, hi)
    if start == end:
        raise ValueError("The interval must have positive duration")
    return run, start, end


def audio(root, start=None, end=None, ffmpeg="ffmpeg"):
    root = Path(root)
    run, start, end = limits(root, start, end)
    src = source(root, run["video"])
    tool_version = version(ffmpeg, "-version")
    tag = fingerprint([src["sha256"], start, end, ffmpeg, tool_version])[:12]
    out = root / "evidence" / "audio" / f"{tag}.wav"
    params = {"start": start, "end": end, "rate": 16000, "channels": 1, "ffmpeg": ffmpeg, "version": tool_version}
    def action():
        out.parent.mkdir(parents=True, exist_ok=True)
        execute([ffmpeg, "-hide_banner", "-nostdin", "-y", "-ss", start, "-i", src["path"],
                 "-t", end-start, "-vn", "-ac", 1, "-ar", 16000, "-c:a", "pcm_s16le", out],
                out.with_suffix(".log"))
        write(out.with_suffix(".json"), {"source": src["id"], "source_sha256": src["sha256"], "offset": start, "end": end,
                                       "mapping": "original = audio_seconds + offset"})
        return [out, out.with_suffix(".json"), out.with_suffix(".log")]
    result = operation(root, f"audio:{tag}", {src["id"]: src["sha256"]}, params, action)
    return out, result


def frame(root, at, ffmpeg="ffmpeg", width=1600):
    root = Path(root)
    run = read(root / "run.json")
    interval(at, at, *run["scope"])
    if width < 100:
        raise ValueError("Frame width must be at least 100 pixels")
    src = source(root, run["video"])
    tool_version = version(ffmpeg, "-version")
    tag = fingerprint([src["sha256"], at, width, ffmpeg, tool_version])[:12]
    out = root / "evidence" / "frames" / f"{tag}.png"
    def action():
        out.parent.mkdir(parents=True, exist_ok=True)
        _, stderr = execute([ffmpeg, "-hide_banner", "-nostdin", "-y", "-ss", at, "-copyts",
                             "-i", src["path"], "-frames:v", 1, "-vf", "showinfo", out],
                            out.with_suffix(".log"))
        times = re.findall(r"\bn:\s*\d+.*?\bpts_time:([\d.eE+-]+)", stderr)
        if not times:
            raise ValueError("FFmpeg did not report source PTS; do not label the frame with a guessed time")
        actual = float(times[0])
        interval(actual, actual, 0, src["duration"])
        if actual < at - 0.1:
            raise ValueError("Unexpected timestamp origin in FFmpeg output; inspect the frame log")
        preview = out.with_name(out.stem + "-read.png")
        execute([ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", out, "-vf",
                 f"scale={width}:-1", "-frames:v", 1, preview], out.with_name(out.stem + "-scale.log"))
        write(out.with_suffix(".json"), {"source": src["id"], "source_sha256": src["sha256"], "requested": at, "time": actual,
                                       "original": relative(root, out), "readable": relative(root, preview)})
        return [out, preview, out.with_suffix(".json"), out.with_suffix(".log")]
    return operation(root, f"frame:{tag}", {src["id"]: src["sha256"]},
                     {"time": at, "width": width, "ffmpeg": ffmpeg, "version": tool_version}, action)


def normalize(parts, source_id, start, end):
    """Keep overlap words by midpoint; retain raw segments separately for boundary review."""
    result = []
    for part in parts:
        offset = part["offset"]
        lo, hi = part["keep"]
        for segment in part["segments"]:
            kept = []
            for word in segment.get("words") or []:
                a, b = word["start"] + offset, word["end"] + offset
                interval(a, b, start, end)
                if lo <= (a + b) / 2 < hi:
                    kept.append(dict(word, start=a, end=b))
            if kept:
                result.append({"id": f"seg-{len(result)+1:06}", "source": source_id,
                               "start": kept[0]["start"], "end": kept[-1]["end"],
                               "text": "".join(w["word"] for w in kept).strip(), "words": kept,
                               "timing": "engine-estimated", "raw": part["raw"],
                               "raw_segment": segment["id"]})
            elif segment["text"].strip() and not segment.get("words"):
                a, b = offset + segment["start"], offset + segment["end"]
                interval(a, b, start, end)
                if lo <= (a+b)/2 < hi:
                    result.append({"id": f"seg-{len(result)+1:06}", "source": source_id,
                                   "start": a, "end": b, "text": segment["text"].strip(),
                                   "timing": "engine-estimated", "raw": part["raw"],
                                   "raw_segment": segment["id"]})
    return result


def transcribe(root, model, language, chunk=300, overlap=4, threads=4, vad=False,
               start=None, end=None, ffmpeg="ffmpeg"):
    root = Path(root)
    run, start, end = limits(root, start, end)
    if chunk <= 0 or not 0 <= overlap < chunk:
        raise ValueError("Require chunk > overlap >= 0")
    model = Path(model).resolve()
    if not model.is_dir():
        raise ValueError("Supply an existing faster-whisper model directory; download models separately")
    src = source(root, run["video"])
    weights = {p.name: sha(p) for p in sorted(model.iterdir()) if p.is_file()}
    versions = {p: importlib.metadata.version(p) for p in ("faster-whisper", "ctranslate2", "av")}
    params = dict(model=str(model), weights=weights, language=language, chunk=chunk, overlap=overlap,
                  threads=threads, vad=vad, start=start, end=end, versions=versions,
                  ffmpeg=ffmpeg, ffmpeg_version=version(ffmpeg, "-version"))
    tag = fingerprint([src["sha256"], params])[:12]
    def action():
        folder = root / "evidence" / "asr" / (tag + "-" + str(time.time_ns()))
        from faster_whisper import WhisperModel
        engine = WhisperModel(str(model), device="cpu", compute_type="int8", cpu_threads=threads,
                              num_workers=1, local_files_only=True)
        parts, files = [], []
        cursor = start
        number = 0
        while cursor < end:
            owner_end = min(cursor+chunk, end)
            a, b = max(start, cursor-overlap/2), min(end, owner_end+overlap/2)
            wav, _ = audio(root, a, b, ffmpeg)
            raw_file = folder / f"part-{number:04}.json"
            segments, info = engine.transcribe(str(wav), language=language, beam_size=5,
                                               temperature=0, condition_on_previous_text=False,
                                               word_timestamps=True, vad_filter=vad)
            raw = []
            for seg in segments:
                item = asdict(seg)
                raw.append(item)
            data = {"offset": a, "keep": [cursor, owner_end], "audio": relative(root, wav),
                    "duration": info.duration, "duration_after_vad": info.duration_after_vad,
                    "language": info.language, "segments": raw, "parameters": params,
                    "source_sha256": src["sha256"]}
            write(raw_file, data)
            parts.append(dict(data, raw=relative(root, raw_file)))
            files.append(raw_file)
            cursor, number = owner_end, number+1
        normalized = normalize(parts, src["id"], start, end)
        out = folder / "segments.jsonl"
        dump_lines(out, normalized)
        write(folder / "index.json", {"source": src["id"], "range": [start, end], "segments": len(normalized),
                                     "parts": [relative(root, p) for p in files], "parameters": params,
                                     "note": "Review chunk boundaries and significant facts; timestamps are estimates."})
        return files + [out, folder / "index.json"]
    return operation(root, f"asr:{tag}", {src["id"]: src["sha256"]}, params, action)
