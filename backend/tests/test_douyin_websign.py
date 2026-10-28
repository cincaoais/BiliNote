import pytest

from app.downloaders.douyin_helper import websign

# Vectors computed by Douyin's own SDK, from Douyin_TikTok_Download_API tests/unit/test_signing.py.
UIFID = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff0011"


@pytest.mark.parametrize(
    "pairs, cookie, timestamp, signature",
    [
        (
            [("device_platform", "webapp"), ("aid", "6383"), ("aweme_id", "123")],
            f"UIFID_TEMP={UIFID}",
            1788848841,
            "6090b6162b96aeb107b51ab69140c764",
        ),
        (
            [("q", "中"), ("z", "a b"), ("e", "/")],
            "UIFID=AAAA1111; UIFID_TEMP=BBBB2222",
            1788848901,
            "a79dcd330ecba4d98016189c3ca313cd",
        ),
        ([], "UIFID=AAAA1111", 1788848901, "0479f3eb2297110d45bfbd96ccccb292"),
    ],
)
def test_signature_matches_douyin_sdk(monkeypatch, pairs, cookie, timestamp, signature):
    monkeypatch.setattr(websign.time, "time", lambda: timestamp)

    query, headers = websign.build_signed_query(pairs, cookie)

    assert query.endswith(f"&x-secsdk-web-signature={signature}")
    assert headers["x-secsdk-web-signature"] == signature
