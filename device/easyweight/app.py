"""The mirror app: camera, window, keys and the main loop.

    python -m easyweight                    # default webcam, "full" model
    python -m easyweight --camera 1         # use a different webcam
    python -m easyweight --model lite       # faster on slower computers
    python -m easyweight --fullscreen       # start fullscreen (for the mirror)
    python -m easyweight --record set.jsonl.gz   # also save the pose to a file
    python -m easyweight --offline          # don't send workouts to the backend

Workouts are sent to the backend once the mirror is registered
(python -m easyweight.register). Without a network they wait on disk.

Keys (also work on a Hebrew keyboard layout):
    F       fullscreen on/off
    D       show/hide the camera picture (handy while testing)
    R       reset the count
    Q, Esc  quit
"""
import argparse
import contextlib
import logging
import sys
import time

import cv2
import mediapipe as mp

from .engine import Engine
from .hud import render
from .pose import MODELS_DIR, create_landmarker, load_model
from .recording import Recorder
from .reporter import Reporter, wall_clock
from .sync import DEVICE_CONFIG, Outbox, Sender, load_device_config

WINDOW = "EasyWeight"
DEFAULT_SIZE = (1280, 720)

# Key codes. The 0x05.. codes are the Hebrew letters on the same keys,
# and "/" is where Q sits on a Hebrew keyboard
KEYS = {
    "quit": {27, ord("q"), ord("Q"), ord("/")},
    "fullscreen": {ord("f"), ord("F"), 0x05DB},  # כ
    "camera": {ord("d"), ord("D"), 0x05D2},      # ג
    "reset": {ord("r"), ord("R"), 0x05E8},       # ר
}


def open_camera(index):
    # DirectShow opens most USB webcams faster and more reliably on Windows
    backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform.startswith("win") else [cv2.CAP_ANY]
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            # Uncompressed 720p is too much for USB (about 4 fps on many webcams),
            # so ask for MJPG. It must come after the size or DirectShow ignores it
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            return cap
        cap.release()
    return None


def window_size():
    try:
        _, _, w, h = cv2.getWindowImageRect(WINDOW)
        if w > 100 and h > 100:
            return w, h
    except cv2.error:
        pass
    return DEFAULT_SIZE


def set_fullscreen(on):
    cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN if on else cv2.WINDOW_NORMAL)


def window_closed():
    try:
        return cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def key_action(code):
    for action, codes in KEYS.items():
        if code in codes:
            return action
    return None


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="EasyWeight rep counter: bicep curls, lateral raises, overhead presses")
    p.add_argument("--camera", type=int, default=0,
                   help="webcam number (try 1 or 2 if 0 is the wrong camera)")
    p.add_argument("--model", choices=["lite", "full", "heavy"], default="full",
                   help="lite = fastest, heavy = most accurate")
    p.add_argument("--models-dir", default=MODELS_DIR,
                   help="folder the pose models are kept in (default: %(default)s)")
    p.add_argument("--fullscreen", action="store_true", help="start in fullscreen")
    p.add_argument("--offline", action="store_true",
                   help="don't send workouts to the backend, even if registered")
    p.add_argument("--device-config", default=DEVICE_CONFIG,
                   help="this mirror's registration (default: %(default)s)")
    p.add_argument("--record", metavar="FILE",
                   help="also save the pose of every frame to FILE (.jsonl or .jsonl.gz), "
                        "to replay later with python -m easyweight.replay")
    return p.parse_args(argv)


def start_sync(args):
    """The reporter, outbox and sender, or Nones when the workouts stay local"""
    config = None if args.offline else load_device_config(args.device_config)
    if config is None:
        if not args.offline:
            print("Not registered with a backend, so workouts aren't saved. "
                  "To save them: python -m easyweight.register "
                  "--name \"My mirror\" --email you@example.com")
        return None, None, None
    outbox = Outbox()
    sender = Sender(outbox, config["api_url"], config["token"]).start()
    print(f'Sending workouts to {config["api_url"]} as "{config.get("name", "this mirror")}"'
          + (f" ({len(outbox)} waiting from before)" if len(outbox) else ""))
    return Reporter(wall_clock()), outbox, sender


def main(argv=None):
    args = parse_args(argv)
    model = load_model(args.model, args.models_dir)
    cap = open_camera(args.camera)
    if cap is None:
        sys.exit(f"Couldn't open webcam {args.camera}. "
                 "Is another app using it? You can also try --camera 1")

    engine = Engine()
    reporter, outbox, sender = start_sync(args)
    fullscreen, show_camera = args.fullscreen, True
    flash_until, failed_reads = 0.0, 0

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, *DEFAULT_SIZE)
    set_fullscreen(fullscreen)

    start = time.perf_counter()
    last_ts = -1
    recorder = None
    with contextlib.ExitStack() as stack:
        if sender:
            stack.callback(sender.stop)  # runs last: sends what's left
            stack.callback(lambda: finish_workout(engine, reporter, outbox))
        stack.callback(cv2.destroyAllWindows)
        stack.callback(cap.release)
        landmarker = stack.enter_context(create_landmarker(model))
        while True:
            ok, frame = cap.read()
            if not ok:
                failed_reads += 1
                if failed_reads > 50:
                    print("The webcam stopped sending frames.")
                    break
                continue
            failed_reads = 0

            now = time.perf_counter()

            # MediaPipe needs RGB images and strictly increasing timestamps
            ts = max(int((now - start) * 1000), last_ts + 1)
            last_ts = ts
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
            landmarks = result.pose_landmarks[0] if result.pose_landmarks else None

            h, w = frame.shape[:2]
            if args.record and recorder is None:  # opened here, once the frame size is known
                recorder = stack.enter_context(Recorder(args.record, w, h, model=args.model))
            if recorder:
                recorder.write(now - start, landmarks)

            if engine.step(landmarks, w, h, now):
                flash_until = now + 0.35
            if reporter:
                outbox.add(reporter.observe(engine.workout, now))

            canvas = render(window_size(), engine.workout, now, flash=now < flash_until,
                            frame=frame if show_camera else None)
            cv2.imshow(WINDOW, canvas)

            action = key_action(cv2.waitKeyEx(1))
            if action == "quit":
                break
            if action == "fullscreen":
                fullscreen = not fullscreen
                set_fullscreen(fullscreen)
            elif action == "camera":
                show_camera = not show_camera
            elif action == "reset":
                engine.reset()
            if window_closed():
                break
    if recorder:
        print(f"Saved the recording to {args.record}")


def finish_workout(engine, reporter, outbox):
    """On quit, end the workout so the backend knows it's over"""
    engine.reset()
    outbox.add(reporter.observe(engine.workout, time.perf_counter()))


def run():
    # The tuning details of every rep go to the terminal
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    try:
        main()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
