"""抖音游客 Cookie：用无头 CloakBrowser 打开抖音首页，等抖音自己的 JS 下发访客 Cookie。

Douyin guest cookies from a headless CloakBrowser. Douyin's own JS sets
``ttwid``, ``s_v_web_id`` and ``UIFID_TEMP``/``UIFID`` in a real browser; the
detail API needs them. Cookie values are never logged.
"""
import logging
import threading
import time
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

DOUYIN_HOME = "https://www.douyin.com/"
REQUIRED_COOKIES = ("ttwid", "s_v_web_id")
VISITOR_ID_COOKIES = ("UIFID", "UIFID_TEMP")

_lock = threading.Lock()
_cached: Optional[str] = None


def has_visitor_cookies(names: Iterable[str]) -> bool:
    """All REQUIRED cookies present and at least one visitor-id cookie present."""
    present = set(names)
    return all(n in present for n in REQUIRED_COOKIES) and any(
        n in present for n in VISITOR_ID_COOKIES
    )


def _to_cookie_header(cookies) -> str:
    """Playwright cookie dicts -> "name=value; name=value" (skips empty names)."""
    return "; ".join(
        f"{c['name']}={c.get('value', '')}" for c in cookies if c.get("name")
    )


def fetch_guest_cookie(timeout: float = 45.0, user_agent: Optional[str] = None) -> str:
    try:
        from cloakbrowser import launch_context
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
    except ImportError as e:
        raise RuntimeError(
            "未安装 cloakbrowser（pip install cloakbrowser），无法自动获取抖音游客 Cookie；"
            "请在 设置 → 下载 中粘贴抖音 Cookie"
        ) from e

    started = time.monotonic()
    deadline = started + timeout
    context = launch_context(headless=True, **({"user_agent": user_agent} if user_agent else {}))
    try:
        page = context.new_page()
        try:
            # 抖音首页偶尔超过超时还在加载，但 Cookie 早已下发，所以导航超时不算失败，继续轮询即可。
            page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=int(timeout * 1000))
        except PlaywrightTimeout:
            logger.warning("抖音首页导航超时，继续等待游客 Cookie")
        while True:
            cookies = context.cookies()
            names = {c.get("name") for c in cookies if c.get("name")}
            if has_visitor_cookies(names):
                logger.info(
                    "抖音游客 Cookie 获取成功，用时 %.1fs，Cookie 名: %s",
                    time.monotonic() - started,
                    sorted(names),
                )
                return _to_cookie_header(cookies)
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"抖音在 {timeout:.0f}s 内没有下发游客 Cookie（已获得: {sorted(names)}）"
                )
            page.wait_for_timeout(500)
    finally:
        context.close()


def get_guest_cookie(refresh: bool = False, user_agent: Optional[str] = None) -> str:
    global _cached
    with _lock:
        if _cached is None or refresh:
            _cached = fetch_guest_cookie(user_agent=user_agent)
        return _cached


def clear_guest_cookie() -> None:
    global _cached
    with _lock:
        _cached = None
