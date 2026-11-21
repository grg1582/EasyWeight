import json

import pytest

from easyweight.recording import Recorder, read_recording
from easyweight.replay import main, replay
from poses import CURLED, FPS, SIZE, reps


def record(path, frames, **extra):
    with Recorder(path, SIZE, SIZE, **extra) as rec:
        for i, landmarks in enumerate(frames):
            rec.write(i / FPS, landmarks)


@pytest.mark.parametrize("name", ["set.jsonl", "set.jsonl.gz"])
def test_round_trip(tmp_path, name):
    frames = reps(CURLED, 2) + [None]
    record(tmp_path / name, frames, model="full")
    header, back = read_recording(tmp_path / name)
    assert header["width"] == SIZE and header["model"] == "full"
    assert len(back) == len(frames)
    assert back[-1] == (pytest.approx((len(frames) - 1) / FPS, abs=1e-3), None)
    t, lm = back[0]
    assert lm[11].x == pytest.approx(frames[0][11].x, abs=1e-4)


def test_replay_counts_like_live(tmp_path):
    record(tmp_path / "curls.jsonl.gz", reps(CURLED, 7))
    assert replay(tmp_path / "curls.jsonl.gz") == [{"exercise": "curl", "set": 1, "reps": 7}]


def test_replay_cli(tmp_path, capsys):
    record(tmp_path / "curls.jsonl", reps(CURLED, 3))
    main([str(tmp_path / "curls.jsonl")])
    assert "curl set 1: 3 reps" in capsys.readouterr().out


def test_rejects_other_files(tmp_path):
    path = tmp_path / "other.jsonl"
    path.write_text(json.dumps({"hello": 1}) + "\n")
    with pytest.raises(ValueError):
        read_recording(path)
