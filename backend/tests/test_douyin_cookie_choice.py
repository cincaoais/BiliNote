import json

import pytest

from app.downloaders import douyin_downloader as dd
from app.downloaders.douyin_helper import browser_cookie

AWEME_ID = "7000000000000000001"
OK = json.dumps({"status_code": 0, "aweme_detail": {"aweme_id": AWEME_ID, "item_title": "t"}}).encode()
BLOCK = b"Blocked by ArgusSecurityPlugin Uifid Not Found"
GONE = json.dumps(
    {"status_code": 0, "aweme_detail": None, "filter_detail": {"filter_reason": "status_audit_not_pass"}}
).encode()
SETTINGS = "UIFID=saved; ttwid=t; s_v_web_id=v"


class FakeResponse:
    def __init__(self, status_code, body: bytes, content_type="application/json"):
        self.status_code = status_code
        self.content = body
        self.text = body.decode("utf-8", errors="replace")
        self.headers = {"Content-Type": content_type}

    def json(self):
        try:
            return json.loads(self.content)
        except json.JSONDecodeError as e:
            raise ValueError(str(e)) from e


def ok():
    return FakeResponse(200, OK)


def block():
    return FakeResponse(200, BLOCK, "text/plain")


def gone():
    return FakeResponse(200, GONE)


class Env:
    def __init__(self):
        self.guest_calls = []
        self.guest_uas = []
        self.get_cookies = []
        self.get_uifids = []
        self.responses = []


@pytest.fixture
def env(monkeypatch):
    e = Env()
    browser_cookie._cached = None
    monkeypatch.setattr(dd.DouyinDownloader, "extract_video_id", lambda self, url: AWEME_ID)
    monkeypatch.setattr(dd.DouyinDownloader, "gen_real_msToken", lambda self: "m" * 128)
    monkeypatch.setattr(dd.ABogus, "get_value", lambda self, params: "abogus")

    def fake_fetch(timeout=30.0, user_agent=None):
        e.guest_calls.append(1)
        e.guest_uas.append(user_agent)
        return f"UIFID_TEMP=guest{len(e.guest_calls)}; ttwid=t; s_v_web_id=v"

    monkeypatch.setattr(browser_cookie, "fetch_guest_cookie", fake_fetch)

    def fake_get(url, headers=None, **kwargs):
        e.get_cookies.append(headers["Cookie"])
        e.get_uifids.append(headers.get("uifid"))
        return e.responses.pop(0)

    monkeypatch.setattr(dd.requests, "get", fake_get)
    yield e
    browser_cookie._cached = None


def set_settings(monkeypatch, cookie):
    monkeypatch.setattr(dd.cfm, "get", lambda platform: cookie)


def test_settings_cookie_wins(env, monkeypatch):
    set_settings(monkeypatch, SETTINGS)
    env.responses = [ok()]
    result = dd.DouyinDownloader().fetch_video_info("https://v.douyin.com/x/")
    assert result["aweme_detail"]["aweme_id"] == AWEME_ID
    assert env.get_cookies == [SETTINGS]
    assert env.guest_calls == []
    assert env.get_uifids == ["saved"]


def test_guest_cookie_when_settings_empty(env, monkeypatch):
    set_settings(monkeypatch, None)
    env.responses = [ok(), ok()]
    d = dd.DouyinDownloader()
    d.fetch_video_info("https://v.douyin.com/x/")
    d.fetch_video_info("https://v.douyin.com/x/")
    assert len(env.guest_calls) == 1
    assert len(env.get_cookies) == 2
    assert all("UIFID_TEMP=guest1" in c for c in env.get_cookies)
    assert env.guest_uas == [dd.DouyinConfig.HEADERS["User-Agent"]]


def test_one_refresh_after_block(env, monkeypatch):
    set_settings(monkeypatch, None)
    env.responses = [block(), ok()]
    result = dd.DouyinDownloader().fetch_video_info("https://v.douyin.com/x/")
    assert result["aweme_detail"]["aweme_id"] == AWEME_ID
    assert len(env.guest_calls) == 2
    assert env.get_cookies == [
        "UIFID_TEMP=guest1; ttwid=t; s_v_web_id=v",
        "UIFID_TEMP=guest2; ttwid=t; s_v_web_id=v",
    ]


def test_block_after_refresh_raises_with_douyin_message(env, monkeypatch):
    set_settings(monkeypatch, None)
    env.responses = [block(), block()]
    with pytest.raises(ValueError) as exc:
        dd.DouyinDownloader().fetch_video_info("https://v.douyin.com/x/")
    assert "Uifid Not Found" in str(exc.value)
    assert "Cookie" in str(exc.value)
    assert len(env.get_cookies) == 2
    assert len(env.guest_calls) == 2


def test_settings_cookie_blocked_falls_back_to_guest(env, monkeypatch):
    set_settings(monkeypatch, SETTINGS)
    env.responses = [block(), ok()]
    result = dd.DouyinDownloader().fetch_video_info("https://v.douyin.com/x/")
    assert result["aweme_detail"]["aweme_id"] == AWEME_ID
    assert env.get_cookies == [SETTINGS, "UIFID_TEMP=guest1; ttwid=t; s_v_web_id=v"]


def test_missing_aweme_detail_raises_reason(env, monkeypatch):
    set_settings(monkeypatch, SETTINGS)
    env.responses = [gone()]
    with pytest.raises(ValueError) as exc:
        dd.DouyinDownloader().fetch_video_info("https://v.douyin.com/x/")
    assert "status_audit_not_pass" in str(exc.value)


def test_has_visitor_cookies():
    assert browser_cookie.has_visitor_cookies({"ttwid", "s_v_web_id", "UIFID_TEMP"})
    assert browser_cookie.has_visitor_cookies({"ttwid", "s_v_web_id", "UIFID"})
    assert not browser_cookie.has_visitor_cookies({"s_v_web_id", "UIFID"})
    assert not browser_cookie.has_visitor_cookies({"ttwid", "s_v_web_id"})
