"""Save the pose landmarks of a session to a file and read them back.

A recording is JSON Lines (one JSON object per line), gzipped when the file
name ends in .gz. The first line is a header:

    {"format": "easyweight-recording", "version": 1, "width": 1280, "height": 720}

and every frame after it is:

    {"t": 1.234, "lm": [[x, y, visibility], ...]}   # 33 landmarks, or null if nobody

A header can also hold "expected": the sets the recording should produce,
as [{"exercise": "curl", "set": 1, "reps": 10}, ...]. The tests use it.
"""
import gzip
import json
from collections import namedtuple
from pathlib import Path

FORMAT = "easyweight-recording"
VERSION = 1

Landmark = namedtuple("Landmark", "x y visibility")


def _open(path, mode):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8")
    return open(path, mode, encoding="utf-8")


class Recorder:
    """Writes frames to a recording. Use it as a context manager"""

    def __init__(self, path, width, height, **extra):
        self.file = _open(path, "w")
        header = {"format": FORMAT, "version": VERSION, "width": width, "height": height}
        header.update(extra)
        self._write(header)

    def _write(self, obj):
        self.file.write(json.dumps(obj, separators=(",", ":")) + "\n")

    def write(self, t, landmarks):
        """Add one frame: its time in seconds and its landmarks (or None)"""
        lm = None
        if landmarks:
            lm = [[round(p.x, 5), round(p.y, 5),
                   None if p.visibility is None else round(p.visibility, 3)]
                  for p in landmarks]
        self._write({"t": round(t, 4), "lm": lm})

    def close(self):
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def read_recording(path):
    """Returns (header, frames): frames is a list of (t, landmarks or None)"""
    with _open(path, "r") as f:
        header = json.loads(f.readline())
        if header.get("format") != FORMAT:
            raise ValueError(f"{path} is not an EasyWeight recording")
        if header.get("version") != VERSION:
            raise ValueError(f"{path}: unsupported recording version {header.get('version')}")
        frames = []
        for line in f:
            if not line.strip():
                continue
            frame = json.loads(line)
            lm = frame["lm"]
            frames.append((frame["t"], [Landmark(*p) for p in lm] if lm else None))
    return header, frames
