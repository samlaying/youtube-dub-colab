"""Job folder for the GPU half, created by unpacking a bundle from Codespaces."""

import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

STAGES = ("s5", "s6")
STAGE_NAMES = {"s5": "tts", "s6": "mix + lipsync"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Job:
    def __init__(self, root):
        self.root = Path(root)
        self.manifest_path = self.root / "manifest.json"
        self.data = {}

    @classmethod
    def load(cls, root):
        job = cls(root)
        if not job.manifest_path.exists():
            raise SystemExit(f"no manifest at {job.manifest_path}; run `unpack` first")
        job.data = json.loads(job.manifest_path.read_text(encoding="utf-8"))
        return job

    @classmethod
    def unpack(cls, bundle, root):
        """Extract a bundle produced by `python3 -m dub bundle` in the Codespace repo."""
        job = cls(root)
        job.root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bundle) as archive:
            names = archive.namelist()
            prefix = names[0].split("/")[0] + "/" if names else ""
            for name in names:
                if not name.startswith(prefix) or name.endswith("/"):
                    continue
                relative = name[len(prefix):]
                target = job.root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, open(target, "wb") as sink:
                    sink.write(source.read())
        job.data = json.loads(job.manifest_path.read_text(encoding="utf-8"))
        return job

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.manifest_path)

    @property
    def video(self):
        return self.root / "source.mp4"

    @property
    def background(self):
        return self.root / "separated" / "no_vocals.wav"

    @property
    def translated_text(self):
        return self.root / "translated" / "zh.txt"

    @property
    def tts_wav(self):
        return self.root / "tts" / "zh.wav"

    @property
    def mixed_wav(self):
        return self.root / "mix" / "final.wav"

    @property
    def output_video(self):
        return self.root / "out" / "final.mp4"

    def done(self, stage):
        return self.data.get("stages", {}).get(stage, {}).get("status") == "done"

    def mark(self, stage, status, **extra):
        record = self.data.setdefault("stages", {}).setdefault(stage, {})
        record.update({"status": status, "updated_at": _now(), **extra})
        self.save()

    def require(self, stage, what):
        if not self.done(stage):
            raise SystemExit(f"{what} missing: stage {stage} has not finished for {self.root.name}")
