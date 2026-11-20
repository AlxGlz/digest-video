"""Resumable CPU ASR with one coordinator, bounded workers, and original-time evidence."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import importlib.metadata
import multiprocessing
import os
from pathlib import Path
import sys
import time
import wave

from common import code_revision, dump_lines, fingerprint, operation, read, relative, sha, source, write


def budget(cpu_budget=2, jobs=1):
    if not isinstance(cpu_budget, int) or not isinstance(jobs, int) or not 1 <= jobs <= cpu_budget:
        raise ValueError("Require 1 <= jobs <= cpu-budget")
    if cpu_budget > (os.cpu_count() or 1):
        raise ValueError("CPU budget exceeds the available logical CPUs")
    return {"jobs": jobs, "threads_per_worker": cpu_budget // jobs,
            "cpu_budget": cpu_budget, "effective_threads": jobs * (cpu_budget // jobs)}


def windows(start, end, chunk, overlap):
    if chunk <= 0 or overlap < 0 or overlap >= chunk or end <= start:
        raise ValueError("Require positive scope/chunk and 0 <= overlap < chunk")
    result = []
    cursor = start
    while cursor < end:
        stop = min(end, cursor + chunk)
        result.append({"keep": [cursor, stop], "offset": max(start, cursor-overlap/2),
                       "end": min(end, stop+overlap/2)})
        cursor = stop
    return result


def model_files(model, engine):
    model = Path(model).resolve()
    if not model.is_dir():
        raise ValueError("Model must be an existing local directory; downloads are separate")
    if engine == "zipformer":
        result = {}
        for key in ("encoder", "decoder", "joiner"):
            candidates = sorted(model.glob(key + "*.onnx"))
            quantized = [p for p in candidates if "int8" in p.name]
            candidates = quantized or candidates
            if len(candidates) != 1:
                raise ValueError(f"Require one unambiguous {key} ONNX model (int8 preferred)")
            result[key] = str(candidates[0])
        result["tokens"] = str(model / "tokens.txt")
    else:
        result = {p.name: str(p) for p in model.iterdir() if p.is_file()}
        if "model.bin" not in result:
            raise ValueError("Missing faster-whisper model.bin")
    return result


def initialize(settings):
    """Each process owns its recognizer; numerical libraries load after thread limits."""
    global _engine, _settings, _load_seconds
    _settings = settings
    threads = str(settings["threads_per_worker"])
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = threads
    os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
    began = time.perf_counter()
    if settings["engine"] == "zipformer":
        import sherpa_onnx
        _engine = sherpa_onnx.OfflineRecognizer.from_transducer(
            **settings["files"], num_threads=int(threads), sample_rate=16000,
            provider="cpu", decoding_method="greedy_search")
    else:
        from faster_whisper import BatchedInferencePipeline, WhisperModel
        model = WhisperModel(settings["model"], device="cpu", compute_type="int8",
                             cpu_threads=int(threads), num_workers=1, local_files_only=True)
        _engine = BatchedInferencePipeline(model) if settings["batch_size"] else model
    _load_seconds = time.perf_counter() - began


def token_words(tokens, timestamps, begin, end):
    """SentencePiece token starts become approximate word intervals within the VAD cut."""
    words = []
    for token, timestamp in zip(tokens, timestamps):
        at = min(end, max(begin, begin + timestamp))
        if token.startswith("▁") or not words:
            words.append({"word": token.replace("▁", " "), "start": at})
        else:
            words[-1]["word"] += token
    for i, word in enumerate(words):
        word["end"] = max(word["start"], words[i+1]["start"] if i+1 < len(words) else end)
    return words


def decode(task):
    import numpy as np
    began = time.perf_counter()
    started_unix = time.time()
    with wave.open(task["audio"], "rb") as reader:
        if (reader.getframerate(), reader.getsampwidth(), reader.getnchannels()) != (16000, 2, 1):
            raise ValueError("Expected mono 16 kHz PCM16 audio")
        reader.setpos(round((task["offset"] - task["audio_offset"]) * 16000))
        samples = np.frombuffer(reader.readframes(round((task["end"]-task["offset"])*16000)),
                                dtype=np.int16).astype(np.float32) / 32768
    if _settings["engine"] == "zipformer":
        from faster_whisper.vad import VadOptions, get_speech_timestamps
        cuts = get_speech_timestamps(samples, VadOptions(**_settings["vad_parameters"]), sampling_rate=16000)
        segments = []
        for cut in cuts:
            stream = _engine.create_stream()
            stream.accept_waveform(16000, samples[cut["start"]:cut["end"]])
            _engine.decode_stream(stream)
            result = stream.result
            begin, end = cut["start"]/16000, cut["end"]/16000
            tokens, stamps = list(result.tokens), list(result.timestamps)
            segments.append({"id": len(segments), "start": begin, "end": end, "text": result.text,
                             "tokens": tokens, "timestamps": stamps,
                             "words": token_words(tokens, stamps, begin, end)})
    else:
        kwargs = dict(language=_settings["language"], beam_size=5, temperature=0,
                      condition_on_previous_text=False, word_timestamps=True,
                      vad_filter=_settings["vad"])
        if _settings["batch_size"]:
            kwargs["batch_size"] = _settings["batch_size"]
        iterator, info = _engine.transcribe(samples, **kwargs)
        segments = [asdict(segment) for segment in iterator]
    value = {"signature": task["signature"], "source": task["source"], "source_sha256": task["source_sha256"], "offset": task["offset"],
             "keep": task["keep"], "segments": segments, "settings": _settings,
             "timing": {"decode_seconds": time.perf_counter()-began, "worker_load_seconds": _load_seconds,
                        "started_unix": started_unix, "finished_unix": time.time(), "pid": os.getpid()}}
    write(Path(task["raw"]), value)
    write(Path(task["raw"] + ".sha256.json"), {"sha256": sha(task["raw"]), "signature": task["signature"]})
    return task["raw"]


def reusable(task):
    try:
        record = read(task["raw"] + ".sha256.json")
        return (record["signature"] == task["signature"] and record["sha256"] == sha(task["raw"])
                and read(task["raw"])["signature"] == task["signature"])
    except (OSError, ValueError, KeyError):
        return False


def transcribe(root, model, language, chunk=300, overlap=4, threads=2, vad=False,
               start=None, end=None, ffmpeg="ffmpeg", engine="whisper", jobs=1, batch_size=0):
    from media import audio, limits, normalize
    began = time.perf_counter()
    root = Path(root).resolve()
    run, start, end = limits(root, start, end)
    layout = windows(start, end, chunk, overlap)
    allocation = budget(threads, jobs)
    if engine not in ("whisper", "zipformer") or batch_size < 0:
        raise ValueError("Unknown engine or negative batch size")
    if engine == "zipformer" and batch_size:
        raise ValueError("batch-size is a Whisper option")
    if batch_size and not vad:
        raise ValueError("Batched Whisper requires explicit --vad; effective settings must be recorded")
    src = source(root, run["video"])
    files = model_files(model, engine)
    packages = ["faster-whisper", "onnxruntime", "numpy"]
    packages += ["sherpa-onnx"] if engine == "zipformer" else ["ctranslate2", "av"]
    settings = {"engine": engine, "model": str(Path(model).resolve()), "files": files,
                "model_sha256": {k: sha(v) for k, v in files.items()}, "language": language,
                "versions": {p: importlib.metadata.version(p) for p in packages}, **allocation,
                "batch_size": batch_size, "vad": True if engine == "zipformer" else vad,
                "vad_parameters": {"threshold": .42, "min_speech_duration_ms": 140,
                    "min_silence_duration_ms": 480, "max_speech_duration_s": 19, "speech_pad_ms": 230}
                    if engine == "zipformer" else {},
                "device": "cpu", "decoding": "greedy_search" if engine == "zipformer" else
                    {"compute_type": "int8", "beam_size": 5, "temperature": 0,
                     "condition_on_previous_text": False, "word_timestamps": True},
                "chunk": chunk, "overlap": overlap, "range": [start, end], "code_revision": code_revision()}
    signature = fingerprint([src["sha256"], settings])
    folder = root / "evidence/asr" / signature[:20]
    def action():
        folder.mkdir(parents=True, exist_ok=True)
        audio_start = time.perf_counter()
        wav, audio_result = audio(root, start, end, ffmpeg)
        audio_seconds = time.perf_counter()-audio_start
        tasks = [dict(part, source=src["id"], source_sha256=src["sha256"], audio=str(wav), audio_offset=start,
                      raw=str(folder / f"part-{i:05}.json"), signature=fingerprint([signature, part]))
                 for i, part in enumerate(layout)]
        pending = [task for task in tasks if not reusable(task)]
        decode_start = time.perf_counter()
        # Workers never mutate run.json. A failed attempt retains hash-verified complete windows.
        if pending:
            with ProcessPoolExecutor(max_workers=jobs, mp_context=multiprocessing.get_context("spawn"),
                                     initializer=initialize, initargs=(settings,)) as pool:
                futures = {pool.submit(decode, task): task for task in pending}
                for done in as_completed(futures):
                    done.result()
                    task = futures[done]
                    print(f"ASR complete {task['keep'][0]:.1f}-{task['keep'][1]:.1f}s", file=sys.stderr, flush=True)
        parallel_seconds = time.perf_counter()-decode_start
        parts, outputs = [], []
        for task in tasks:
            raw = Path(task["raw"])
            value = read(raw)
            value["raw"] = relative(root, raw)
            parts.append(value)
            outputs.extend([raw, Path(str(raw)+".sha256.json")])
        segments = normalize(parts, src["id"], start, end)
        segments.sort(key=lambda s: (s["start"], s["end"]))
        for i, segment in enumerate(segments):
            segment["id"] = f"seg-{i+1:06}"
        dump_lines(folder / "segments.jsonl", segments)
        elapsed = time.perf_counter()-began
        write(folder / "index.json", {"source": src["id"], "source_sha256": src["sha256"],
            "settings": settings, "range": [start, end], "segments": len(segments),
            "audio": {"path": relative(root, wav), "sha256": sha(wav), "offset": start},
            "raw": [relative(root, Path(t["raw"])) for t in tasks],
            "mapping": "VAD/word time + audio window offset once; midpoint ownership with overlap",
            "timing": {"wall_seconds": elapsed, "audio_seconds": audio_seconds,
                "workers_wall_seconds": parallel_seconds, "reused_windows": len(tasks)-len(pending),
                "new_windows": len(pending), "realtime_factor": elapsed/(end-start),
                "estimated_scope_seconds": elapsed/(end-start)*(run["scope"][1]-run["scope"][0]),
                "estimate_note": "Pilot extrapolation only; setup, source hashing, content and caches affect runtime"}})
        return outputs + [folder / "segments.jsonl", folder / "index.json"]
    return operation(root, "asr:"+signature[:20], {src["id"]: src["sha256"]}, settings, action)
