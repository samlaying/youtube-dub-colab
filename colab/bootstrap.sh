#!/usr/bin/env bash
# Prepare a Colab VM for the GPU stages (s5 synthesize, s6 mix + lip-sync).
# Run from the repository root:  !bash colab/bootstrap.sh
set -euo pipefail

command -v ffmpeg >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq ffmpeg; }

python3 - <<'PY'
import sys
try:
    import torch
except ImportError:
    sys.exit("torch missing: this repository expects the GPT-SoVITS environment")
print(f"torch {torch.__version__} | cuda available: {torch.cuda.is_available()}")
if not torch.cuda.is_available():
    print("WARNING: no GPU attached; s5/s6 will be impractically slow", file=sys.stderr)
PY

pip install -q "soundfile>=0.12.0"
echo "[bootstrap] done"
