"""Tests for ingest's retrying fetch, with a mocked HTTP session (no network)."""
from unittest.mock import MagicMock

import pytest
import requests

from scout.ingest import RETRY_WAITS_S, fetch_json


def response(json_data=None, status=200):
    r = MagicMock()
    r.json.return_value = json_data
    r.raise_for_status.side_effect = requests.HTTPError(f"{status}") if status >= 400 else None
    return r


def session(*outcomes):
    """A session whose get() returns or raises each outcome in turn."""
    s = MagicMock()
    s.get.side_effect = list(outcomes)
    return s


def test_success_needs_no_retry():
    waits = []
    assert fetch_json("x", session(response({"ok": 1})), sleep=waits.append) == {"ok": 1}
    assert waits == []


def test_retries_with_backoff_then_succeeds():
    waits = []
    s = session(requests.ConnectionError("down"), response(status=503), response({"ok": 1}))
    assert fetch_json("x", s, sleep=waits.append) == {"ok": 1}
    assert waits == [2, 4] and s.get.call_count == 3


def test_gives_up_after_three_retries():
    waits = []
    s = session(*[requests.Timeout("slow")] * 4)
    with pytest.raises(requests.Timeout):
        fetch_json("x", s, sleep=waits.append)
    assert waits == list(RETRY_WAITS_S) == [2, 4, 8]
    assert s.get.call_count == 4                       # first try + 3 retries


def test_bad_json_is_retried():
    bad = response()
    bad.json.side_effect = ValueError("not JSON")
    waits = []
    assert fetch_json("x", session(bad, response([1])), sleep=waits.append) == [1]
    assert waits == [2]
