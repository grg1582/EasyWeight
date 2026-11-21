"""Run a recording through the rep counter and print the sets it finds. Needs
no camera and no pose model.

    python -m easyweight.replay recordings/curls_10.jsonl.gz
"""
import argparse
import logging
import sys

from .engine import Engine
from .recording import read_recording


def replay(path):
    """Returns the sets found in the recording, like Workout.history"""
    header, frames = read_recording(path)
    engine = Engine()
    for t, landmarks in frames:
        engine.step(landmarks, header["width"], header["height"], t)
    return engine.workout.history


def main(argv=None):
    p = argparse.ArgumentParser(description="Count the reps in EasyWeight recordings")
    p.add_argument("paths", nargs="+", help="recording files (.jsonl or .jsonl.gz)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="also print the tuning details of every rep")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(message)s", stream=sys.stdout)
    for path in args.paths:
        print(path)
        sets = replay(path)
        if not sets:
            print("  no reps")
        for s in sets:
            print(f"  {s['exercise']} set {s['set']}: {s['reps']} reps")


if __name__ == "__main__":
    main()
