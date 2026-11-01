"""GPU-side settings; all paths come from the environment."""

import os


class ConfigError(SystemExit):
    pass


def get(name, default=None, required=False):
    value = os.environ.get(name) or default
    if required and not value:
        raise ConfigError(f"{name} is required but not set")
    return value


def tts():
    return {
        "repo": get("GPT_SOVITS_DIR", "/content/GPT-SoVITS"),
        "python": get("GPT_SOVITS_PYTHON", "/content/miniforge3/envs/GPTSoVITS/bin/python"),
        "experiment": get("TTS_EXP", "voice"),
        "sovits": get("SOVITS_PATH", ""),
        "gpt": get("GPT_PATH", ""),
        "ref_audio": get("REF_AUDIO", ""),
        "ref_text": get("REF_TEXT", ""),
        "temperature": get("TTS_TEMPERATURE", "1.0"),
        "fragment_interval": get("TTS_FRAGMENT_INTERVAL", "0.3"),
    }


def lipsync():
    return {
        "repo": get("VIDEO_RETALKING_DIR", ""),
        "python": get("VIDEO_RETALKING_PYTHON", "python3"),
    }
