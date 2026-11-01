"""GPU half of the dubbing pipeline (Colab).

    python3 -m dub unpack --bundle /content/demo.zip --job /content/jobs/demo
    python3 -m dub run    --job /content/jobs/demo --stages s5,s6
    python3 -m dub status --job /content/jobs/demo
"""

import argparse
import sys
from pathlib import Path

from . import stages
from .job import STAGES, STAGE_NAMES, Job


def cmd_unpack(args):
    job = Job.unpack(Path(args.bundle).resolve(), Path(args.job).resolve())
    print(f"unpacked {args.bundle} into {job.root}")
    for stage in STAGES:
        if job.done(stage):
            print(f"  {stage} already done")
    return 0


def cmd_run(args):
    job = Job.load(Path(args.job).resolve())
    selected = STAGES if args.stages == "all" else [s.strip() for s in args.stages.split(",") if s.strip()]
    unknown = [s for s in selected if s not in STAGES]
    if unknown:
        raise SystemExit(f"unknown stages: {', '.join(unknown)} (expected {', '.join(STAGES)})")

    for stage in selected:
        if job.done(stage) and not args.force:
            print(f"[skip] {stage} {STAGE_NAMES[stage]} already done")
            continue
        print(f"\n== {stage} {STAGE_NAMES[stage]}")
        job.mark(stage, "running")
        try:
            info = stages.REGISTRY[stage](job) or {}
        except SystemExit as exc:
            job.mark(stage, "failed", error=str(exc))
            print(f"[fail] {stage}: {exc}")
            return 1
        job.mark(stage, "done", **info)
        print(f"[ok] {stage}")
    print("\nall requested stages finished")
    return 0


def cmd_status(args):
    job = Job.load(Path(args.job).resolve())
    print(f"job  {job.data.get('id')}")
    for stage in STAGES:
        record = job.data.get("stages", {}).get(stage, {})
        print(f"  {stage} {STAGE_NAMES[stage]:16} {record.get('status', 'pending'):8} {record.get('error', '')}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="dub", description="synthesize, mix and lip-sync")
    sub = parser.add_subparsers(dest="command", required=True)

    unpack = sub.add_parser("unpack", help="unpack a bundle from the Codespace repo")
    unpack.add_argument("--bundle", required=True)
    unpack.add_argument("--job", required=True)
    unpack.set_defaults(func=cmd_unpack)

    run = sub.add_parser("run", help="run stages s5..s6")
    run.add_argument("--job", required=True)
    run.add_argument("--stages", default="all")
    run.add_argument("--force", action="store_true")
    run.set_defaults(func=cmd_run)

    status = sub.add_parser("status", help="show stage progress")
    status.add_argument("--job", required=True)
    status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
