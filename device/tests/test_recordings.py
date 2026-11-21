"""Real recordings made at the mirror with --record. Each one whose header
has "expected" sets is replayed, and must give exactly those sets, so a change
to the counting logic can't silently break real-world counting.

See recordings/README.md for how to add one."""
from pathlib import Path

import pytest

from easyweight.recording import read_recording
from easyweight.replay import replay

RECORDINGS = sorted(p for p in (Path(__file__).parent / "recordings").glob("*.jsonl*"))
WITH_EXPECTED = [p for p in RECORDINGS if "expected" in read_recording(p)[0]]


@pytest.mark.skipif(not WITH_EXPECTED, reason="no recordings with expected sets yet")
@pytest.mark.parametrize("path", WITH_EXPECTED, ids=lambda p: p.name)
def test_recording(path):
    header, _ = read_recording(path)
    assert replay(path) == header["expected"]
