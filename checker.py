"""
checker.py — проверка стримов ТОЛЬКО по публичным URL.
Стримеру не нужно давать никаких прав и доступов.

ИСПРАВЛЕНИЯ в этой версии:
  - VK Play Live: исправлена обработка ответа API (был краш 'list has no .get')
  - VK группа: теперь использует VK_SERVICE_TOKEN вместо VK_TOKEN
  - STREAM_LINK_DOMAINS: добавлены youtube.com/live и live.vkvideo.ru
"""
import logging, re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import config

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
S = requests.Session()
S.headers.update(HEADERS)


# ─── Вспомогательные функции ───────────────────────────────────

def _slug(url: str) -> str:
    """Последний значимый сегмент пути из URL."""
    if not url:
        return ""
    path = urlparse(url).path.strip("/").split("/")
    parts = [p for p in path if p and p not in ("live", "stream", "streams", "c", "user")]
    return parts[-1].lstrip("@") if parts else ""

def _yt_channel_id(url: str) -> str:
    """Извлечь channel ID или handle из YouTube URL."""
    path = urlparse(url).path.strip("/").split("/")
    for i, p in enumerate(path):
        if p == "channel" and i + 1 < len(path):
            return path[i + 1]
        if p.startswith("@"):
            return p
        if p in ("c", "user") and i + 1 < len(path):
            return path[i + 1]
    return path[-1] if path else ""

def _is_stream_post(text: str) -> bool:
    """Является ли текст поста анонсом стрима."""
    text_lower = text.lower()
    for domain in config.STREAM_LINK_DOMAINS:
        if domain in text_lower:
            return True
    hits = sum(1 for kw in config.STREAM_KEYWORDS if kw in text_lower)
    return hits >= config.KEYWORD_MIN_MATCHES


# ─── Twitch ────────────────────────────────────────────────────

_tw_token: str | None = None

def _tw_oauth() -> str | None:
    global _tw_token
    if _tw_token:
        return _tw_token
    if not (config.TWITCH_CLIENT_ID and config.TWITCH_CLIENT_SECRET):
        return None
    try:
        r = S.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": config.TWITCH_CLIENT_ID,
            "client_secret": config.TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }, timeout=10)
        _tw_token = r.json().get("access_token")
        return _tw_token
    except Exception as e:
        log.error("Twitch OAuth: %s", e)
        return None

def check_twitch(url: str) -> bool:
    login = _slug(url)
    if not login:
        return False
    token = _tw_oauth()
    if token:
        try:
            r = S.get("https://api.twitch.tv/helix/streams",
                      params={"user_login": login},
                      headers={"Client-ID": config.TWITCH_CLIENT_ID,
                               "Authorization": f"Bearer {token}"},
                      timeout=10)
            return bool(r.json().get("data"))
        except Exception as e:
            log.warning("Twitch API: %s — fallback HTML", e)
    try:
        r = S.get(url, timeout=15)
        return "isLiveBroadcast" in r.text or "В ЭФИРЕ" in r.text
    except Exception as e:
        log.error("Twitch HTML: %s", e)
    return False


# ─── YouTube ───────────────────────────────────────────────────

def check_youtube(url: str) -> bool:
    if not url:
        return False
    if config.YOUTUBE_API_KEY:
        ch_id = _yt_channel_id(url)
        try:
            r = S.get("https://www.googleapis.com/youtube/v3/search", params={
                "part": "snippet", "channelId": ch_id,
                "eventType": "live", "type": "video",
                "key": config.YOUTUBE_API_KEY,
            }, timeout=10)
            return bool(r.json().get("items"))
        except Exception as e:
            log.warning("YT API: %s — fallback HTML", e)
    live_url = url if url.endswith("/live") else url.rstrip("/") + "/live"
    try:
        r = S.get(live_url, timeout=15)
        return ('"liveBroadcastContent":"live"' in r.text or
                "isLiveBroadcast" in r.text or
                "ЭФИР" in r.text)
    except Exception as e:
        log.error("YT HTML: %s", e)
    return False


# ─── Kick ──────────────────────────────────────────────────────

def check_kick(url: str) -> bool:
    login = _slug(url)
    if not login:
        return False
    try:
        r = S.get(f"https://kick.com/api/v1/channels/{login}", timeout=15)
        return bool(r.json().get("livestream"))
    except Exception:
        pass
    try:
        r = S.get(url, timeout=15)
        return "bg-green-500" in r.text and "LIVE" in r.text
    except Exception as e:
        log.error("Kick: %s", e)
    return False


# ─── VK Play Live ─────────────────────────────────────────────
# ИСПРАВЛЕНО: API может возвращать список вместо словаря

def check_vkplay(url: str) -> bool:
    login = _slug(url)
    if not login:
        return False
    try:
        r = S.get(
            f"https://api.vkplay.live/v1/blog/{login}/public_video_stream",
            timeout=15
        )
        data = r.json()

        # API может вернуть словарь {"data": {...}} ИЛИ список [...]
        if isinstance(data, list):
            # Ищем запись с isOnline=True среди элементов списка
            return any(
                item.get("isOnline") or item.get("data", {}).get("isOnline")
                for item in data if isinstance(item, dict)
            )
        elif isinstance(data, dict):
            return bool(data.get("data", {}).get("isOnline"))

    except Exception:
        pass

    # Fallback: HTML
    try:
        r = S.get(url, timeout=15)
        return "StreamStatus_isOnline" in r.text or '"isOnline":true' in r.text
    except Exception as e:
        log.error("VKPlay: %s", e)
    return False


# ─── Telegram канал (публичный) ────────────────────────────────

def check_telegram(url: str) -> bool:
    channel = _slug(url)
    if not channel:
        return False
    try:
        r = S.get(f"https://t.me/s/{channel}", timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        posts = soup.find_all(class_="tgme_widget_message_wrap")[-5:]
        for post in posts:
            text = post.get_text(separator=" ")
            links = [a.get("href", "") for a in post.find_all("a")]
            full = text + " " + " ".join(links)
            if _is_stream_post(full):
                return True
    except Exception as e:
        log.error("Telegram: %s", e)
    return False


# ─── Группа ВК (публичная) ────────────────────────────────────
# ИСПРАВЛЕНО: использует VK_SERVICE_TOKEN вместо VK_TOKEN

def check_vk_group(url: str) -> bool:
    """
    Читает последние посты публичной группы ВК.
    Использует сервисный ключ (VK_SERVICE_TOKEN) — стример ничего не даёт.
    """
    domain = _slug(url)
    if not domain:
        return False
    try:
        r = requests.get("https://api.vk.com/method/wall.get", params={
            "domain": domain,
            "count": 5,
            "access_token": config.VK_SERVICE_TOKEN,
            "v": "5.199",
        }, timeout=10)
        items = r.json().get("response", {}).get("items", [])
        for post in items:
            text = post.get("text", "")
            attachments = post.get("attachments", [])
            extra_urls = " ".join(
                a.get("link", {}).get("url", "")
                for a in attachments if a.get("type") == "link"
            )
            # Ссылки прямо в тексте
            inline = " ".join(re.findall(r'https?://\S+', text))
            if _is_stream_post(text + " " + extra_urls + " " + inline):
                return True
    except Exception as e:
        log.error("VK group: %s", e)
    return False


# ─── Общая проверка одного стримера ───────────────────────────

PLATFORMS = [
    ("twitch",   "🟣 Twitch",       check_twitch,   lambda s: s.get("twitch", "")),
    ("youtube",  "🔴 YouTube",      check_youtube,  lambda s: s.get("youtube", "")),
    ("kick",     "🟢 Kick",         check_kick,     lambda s: s.get("kick", "")),
    ("vkplay",   "🔵 VK Play Live", check_vkplay,   lambda s: s.get("vkplay", "")),
    ("telegram", "✈️ Telegram",     check_telegram, lambda s: s.get("telegram", "")),
    ("vk_group", "💙 ВКонтакте",    check_vk_group, lambda s: s.get("vk_group", "")),
]

def check_streamer(streamer: dict) -> list[dict]:
    """Проверяет все платформы стримера. Возвращает список {platform, icon, is_live, url}."""
    results = []
    for pid, icon, fn, get_url in PLATFORMS:
        url = get_url(streamer)
        if not url:
            continue
        try:
            live = fn(url)
        except Exception as e:
            log.error("check %s/%s: %s", streamer["id"], pid, e)
            live = False
        results.append({"platform": pid, "icon": icon, "is_live": live, "url": url})
    return results
