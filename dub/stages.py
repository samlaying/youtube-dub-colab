"""GPU stages: voice synthesis with the fine-tuned weights, then mix and lip-sync."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config


def run(cmd, cwd=None, env=None, capture=False):
    printable = " ".join(str(part) for part in cmd)
    print(f"  $ {printable}", flush=True)
    result = subprocess.run(
        [str(part) for part in cmd], cwd=cwd, env=env, text=True, capture_output=capture
    )
    if result.returncode != 0:
        if capture:
            sys.stderr.write(result.stdout or "")
            sys.stderr.write(result.stderr or "")
        raise SystemExit(f"command failed ({result.returncode}): {printable}")
    return result


def require_tool(name):
    if shutil.which(name) is None:
        raise SystemExit(f"{name} not found on PATH")


def s5_tts(job):
    """Synthesize translated/zh.txt with the fine-tuned GPT-SoVITS voice."""
    settings = config.tts()
    repo = Path(settings["repo"])
    if not repo.exists():
        raise SystemExit(f"GPT-SoVITS not found at {repo}; set GPT_SOVITS_DIR")
    if not job.translated_text.exists():
        raise SystemExit(f"missing {job.translated_text}; unpack a bundle first")

    helper = Path(__file__).with_name("gpt_sovits_infer.py")
    env = os.environ.copy()
    env.update(
        {
            "TTS_REPO": str(repo),
            "TTS_EXP": settings["experiment"],
            "TEXT_FILE": str(job.translated_text),
            "OUT": str(job.tts_wav),
            "REF_AUDIO": settings["ref_audio"],
            "REF_TEXT": settings["ref_text"],
            "TEMPERATURE": settings["temperature"],
            "FRAGMENT_INTERVAL": settings["fragment_interval"],
            "MPLBACKEND": "Agg",
        }
    )
    if settings["sovits"]:
        env["SOVITS_PATH"] = settings["sovits"]
    if settings["gpt"]:
        env["GPT_PATH"] = settings["gpt"]

    job.tts_wav.parent.mkdir(parents=True, exist_ok=True)
    run([settings["python"], str(helper)], env=env)
    if not job.tts_wav.exists():
        raise SystemExit("TTS produced no audio")
    return {"wav": str(job.tts_wav)}


def s6_mix(job):
    """Blend the dub with the original background, then optionally re-time the mouth."""
    require_tool("ffmpeg")
    if not job.tts_wav.exists():
        raise SystemExit(f"missing {job.tts_wav}; run s5 first")

    background_gain = os.environ.get("BACKGROUND_GAIN", "0.35")
    job.mixed_wav.parent.mkdir(parents=True, exist_ok=True)
    run(
        ["ffmpeg", "-y", "-i", job.tts_wav, "-i", job.background,
         "-filter_complex",
         f"[0:a]aresample=44100[v];"
         f"[1:a]aresample=44100,volume={background_gain}[bg];"
         f"[v][bg]amix=inputs=2:duration=longest:normalize=0[mixed];"
         f"[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[out]",
         "-map", "[out]", job.mixed_wav],
        capture=True,
    )

    settings = config.lipsync()
    job.output_video.parent.mkdir(parents=True, exist_ok=True)
    if settings["repo"] and Path(settings["repo"]).exists():
        run(
            [settings["python"], "inference.py",
             "--face", str(job.video),
             "--audio", str(job.mixed_wav),
             "--outfile", str(job.output_video)],
            cwd=settings["repo"],
        )
        mode = "video-retalking"
    else:
        run(
            ["ffmpeg", "-y", "-i", job.video, "-i", job.mixed_wav,
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-shortest",
             job.output_video],
            capture=True,
        )
        mode = "mux-only"
    return {"video": str(job.output_video), "mode": mode}


REGISTRY = {"s5": s5_tts, "s6": s6_mix}
