"""
Douyin's ``x-secsdk-web-signature`` for sign-protected web API endpoints.

Ported from https://github.com/Evil0ctal/Douyin_TikTok_Download_API
(src/dtk/signing/native/websign.py), Copyright 2021-2026 Evil0ctal and
contributors, licensed under the Apache License 2.0. Changes: the visitor
parameters are read from a Cookie header and appended here, and the API is
reduced to the single call ``douyin_downloader`` makes.

Without it, ``/aweme/v1/web/aweme/detail/`` answers
``403 Blocked by ArgusSecurityPlugin Uifid Not Found`` or ``Signature Not Found``.
"""
import hashlib
import time
from typing import Iterable, Optional
from urllib.parse import quote


def _encode(pairs: list[tuple[str, str]]) -> str:
    # Serialize like the SDK's URLSearchParams: these exact bytes are hashed and sent.
    return "&".join(f"{quote(k, safe='*-._')}={quote(v, safe='*-._')}" for k, v in pairs)


def build_signed_query(pairs: Iterable[tuple], cookie: Optional[str]) -> tuple[str, dict[str, str]]:
    """Return the query string and extra headers for a sign-protected request.

    ``pairs`` are the query parameters in send order, ``a_bogus`` last. The
    visitor parameters come from the Cookie header the request carries:
    ``verifyFp`` and ``fp`` are ``s_v_web_id``, ``uifid`` is ``UIFID`` (or
    ``UIFID_TEMP`` for a guest). A cookie without a visitor id is left unsigned.
    """
    jar = dict(part.strip().split("=", 1) for part in (cookie or "").split(";") if "=" in part)
    covered = [(str(k), str(v)) for k, v in pairs]
    uifid = jar.get("UIFID") or jar.get("UIFID_TEMP")
    if not uifid:
        return _encode(covered), {}
    if jar.get("s_v_web_id"):
        covered += [("verifyFp", jar["s_v_web_id"]), ("fp", jar["s_v_web_id"])]
    timestamp = str(int(time.time()))
    covered += [("uifid", uifid), ("timestamp", timestamp)]
    query = _encode(covered)
    # The salt is string #39 of the douyin_web secsdk VM (@byted/secsdk-strategy v1.0.40).
    signature = hashlib.md5(f"{uifid}_{timestamp}_A96D855A08C0A9707F8BEF0D9A527E4E_{query}".encode()).hexdigest()
    headers = {"uifid": uifid, "x-secsdk-web-signature": signature, "x-secsdk-web-expire": timestamp}
    return f"{query}&x-secsdk-web-signature={signature}", headers
