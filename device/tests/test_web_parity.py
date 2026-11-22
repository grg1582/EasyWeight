"""The browser's copy of the counting logic is tested against poses and
results saved by web_parity.py. This checks that file still matches what the
Python counter does, so the two can't drift apart unnoticed."""
import json

import pytest
from web_parity import PARITY_FILE, build, dump


@pytest.mark.skipif(not PARITY_FILE.parent.exists(), reason="the web folder isn't here")
def test_parity_file_is_up_to_date():
    assert PARITY_FILE.exists(), "Run python tests/web_parity.py to make it"
    saved = json.loads(PARITY_FILE.read_text(encoding="utf-8"))
    assert saved == json.loads(dump(build())), (
        "The counting logic changed: run python tests/web_parity.py, "
        "then check the web tests still pass")
