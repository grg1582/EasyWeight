"""Run a recording through the rep counter and print the sets it finds. Needs
no camera and no pose model.

    python -m easyweight.replay recordings/curls_10.jsonl.gz
    python -m easyweight.replay recordings/curls_10.jsonl.gz --send   # also to the backend

With --send the workout is sent to the backend as if it happened just now, using
this mirror's registration (python -m easyweight.register).
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timezone

from .engine import Engine
from .recording import read_recording
from .reporter import Reporter
from .sync import DEVICE_CONFIG, Outbox, Sender, load_device_config


def replay(path, reporter=None):
    """Returns the sets found in the recording, like Workout.history. With a
    reporter, also returns the events it produced"""
    header, frames = read_recording(path)
    engine = Engine()
    events = []
    for t, landmarks in frames:
        engine.step(landmarks, header["width"], header["height"], t)
        if reporter:
            events += reporter.observe(engine.workout, t)
    if reporter:
        engine.reset()
        events += reporter.observe(engine.workout, t)
        return engine.workout.history, events
    return engine.workout.history


def send(path, config):
    """Replay a recording and send its events, dated as if it ended just now"""
    _, frames = read_recording(path)
    start = time.time() - (frames[-1][0] if frames else 0)
    reporter = Reporter(lambda t: datetime.fromtimestamp(start + t, timezone.utc))
    sets, events = replay(path, reporter)
    outbox = Outbox(":memory:")
    outbox.add(events)
    result = "sent"
    while len(outbox) and result == "sent":
        result = Sender(outbox, config["api_url"], config["token"]).send_once()
    if len(outbox):
        sys.exit(f"  couldn't send to {config['api_url']} ({result})")
    print(f"  sent {len(events)} events to {config['api_url']}")
    return sets


def main(argv=None):
    p = argparse.ArgumentParser(description="Count the reps in EasyWeight recordings")
    p.add_argument("paths", nargs="+", help="recording files (.jsonl or .jsonl.gz)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="also print the tuning details of every rep")
    p.add_argument("--send", action="store_true",
                   help="also send the workout to the backend this mirror is registered with")
    p.add_argument("--device-config", default=DEVICE_CONFIG,
                   help="this mirror's registration (default: %(default)s)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(message)s", stream=sys.stdout)
    config = None
    if args.send:
        config = load_device_config(args.device_config)
        if config is None:
            sys.exit("Not registered. First run: python -m easyweight.register --name ...")
    for path in args.paths:
        print(path)
        sets = send(path, config) if config else replay(path)
        if not sets:
            print("  no reps")
        for s in sets:
            print(f"  {s['exercise']} set {s['set']}: {s['reps']} reps")


if __name__ == "__main__":
    main()
