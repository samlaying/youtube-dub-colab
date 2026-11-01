# youtube-dub-colab

GPU half of the dubbing pipeline: take a bundle from the Codespace repo, speak
the translated text in the fine-tuned GPT-SoVITS voice, blend it over the
original background, and re-time the mouth.

```
bundle.zip ──> s5 synthesize ──> s6 mix + lipsync ──> out/final.mp4
                GPT-SoVITS         ffmpeg (+ video-retalking)
```

Part of a three-repository setup:

| Repository | Role | Where it runs |
|---|---|---|
| `youtube-rss-api` | resolve channels/videos, RSS feeds | server with a domain |
| `youtube-dub-codespace` | download, Demucs separation, WhisperX, translation | GitHub Codespaces |
| **`youtube-dub-colab`** (this one) | voice synthesis, mixing, lip-sync | Google Colab (T4) |

Only this half needs CUDA; the other two run on CPU.

## Quick start

```python
!git clone https://github.com/samlaying/youtube-dub-colab
%cd youtube-dub-colab
!bash colab/bootstrap.sh
!python3 -m dub unpack --bundle /content/demo.zip --job /content/jobs/demo
```

With GPT-SoVITS already restored in the VM:

```python
%env GPT_SOVITS_DIR=/content/GPT-SoVITS
%env GPT_SOVITS_PYTHON=/content/miniforge3/envs/GPTSoVITS/bin/python
%env TTS_EXP=myvoice
%env REF_AUDIO=/content/ref.wav
%env REF_TEXT=<transcript of the reference clip>
!python3 -m dub run --job /content/jobs/demo --stages s5,s6
```

`out/final.mp4` is the result.

## Stages

| Stage | Tool | Output |
|---|---|---|
| `s5` synthesize | GPT-SoVITS (`TTS_infer_pack`) | `tts/zh.wav` |
| `s6` mix + lipsync | `ffmpeg`, optional `video-retalking` | `mix/final.wav`, `out/final.mp4` |

Both stages are skipped on re-run unless `--force` is passed.

## Weights

`s5` looks for fine-tuned weights in the GPT-SoVITS checkout:

```
SoVITS_weights_v2/<TTS_EXP>_e*_s*.pth
GPT_weights_v2/<TTS_EXP>-e*.ckpt
```

Set `SOVITS_PATH` / `GPT_PATH` to override the discovery. Weights are 80–150 MB
each and must not be committed: GitHub rejects files over 100 MB without LFS.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `GPT_SOVITS_DIR` | `/content/GPT-SoVITS` | checkout with `TTS_infer_pack` |
| `GPT_SOVITS_PYTHON` | `/content/miniforge3/envs/GPTSoVITS/bin/python` | interpreter that can import it |
| `TTS_EXP` | `voice` | weight prefix |
| `SOVITS_PATH` / `GPT_PATH` | discovered | explicit weights |
| `REF_AUDIO` / `REF_TEXT` | — | reference clip and its transcript, required |
| `TTS_TEMPERATURE` / `TTS_FRAGMENT_INTERVAL` | `1.0` / `0.3` | expressiveness |
| `BACKGROUND_GAIN` | `0.35` | how loud the original background stays |
| `VIDEO_RETALKING_DIR` | — | set it to enable lip-sync |

Without `VIDEO_RETALKING_DIR` stage `s6` still produces a file: it keeps the
original picture and replaces the audio track, so a missing lip-sync checkout
does not block the job.

## Mixing

`amix` without `normalize=0` lowers every input as inputs are added, which
quietens both the dub and the background. The mix here uses
`amix=inputs=2:duration=longest:normalize=0` with a 0.35 gain on the background,
followed by `loudnorm` to -16 LUFS.

## Security

- No credentials are read or stored here; the Colab VM supplies the paths.
- Weights, reference clips and job folders are gitignored.
- Use this on material you own or are licensed to localize. Cloning a voice and
  re-timing a real person's mouth onto speech they never gave is impersonation
  unless the person consented.
