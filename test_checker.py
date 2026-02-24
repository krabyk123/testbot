"""
test_checker.py — ручная проверка всех источников.
Запуск: python test_checker.py
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import config

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}
S = requests.Session()
S.headers.update(HEADERS)
SEP = "─" * 60


def slug(url):
    if not url:
        return ""
    path = urlparse(url).path.strip("/").split("/")
    parts = [p for p in path if p and p not in ("live", "stream", "streams", "c", "user")]
    return parts[-1].lstrip("@") if parts else ""

def mark(cond):
    return f"{GREEN}✅ ДА{RESET}" if cond else f"{RED}❌ НЕТ{RESET}"

def check_keywords(text):
    text_lower = text.lower()
    found_kw    = [kw for kw in config.STREAM_KEYWORDS if kw in text_lower]
    found_links = [d for d in config.STREAM_LINK_DOMAINS if d in text_lower]
    is_live = bool(found_links) or len(found_kw) >= config.KEYWORD_MIN_MATCHES
    return found_kw, found_links, is_live


# ── Telegram ──────────────────────────────────────────────────

def test_telegram(url):
    channel = slug(url)
    if not channel:
        print(f"  {RED}URL пустой{RESET}"); return
    print(f"  Канал: @{channel}")
    try:
        r = S.get(f"https://t.me/s/{channel}", timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        posts = soup.find_all(class_="tgme_widget_message_wrap")[-5:]
        if not posts:
            print(f"  {YELLOW}⚠ Постов не найдено (закрытый канал или неверный адрес){RESET}")
            return
        print(f"  Найдено постов: {len(posts)}\n")
        any_live = False
        for i, post in enumerate(posts, 1):
            text = post.get_text(separator=" ").strip()
            links = [a.get("href", "") for a in post.find_all("a") if a.get("href")]
            stream_links = [l for l in links if any(d in l for d in config.STREAM_LINK_DOMAINS)]
            full = text + " " + " ".join(links)
            found_kw, found_links, is_live = check_keywords(full)
            any_live = any_live or is_live
            print(f"  {CYAN}── Пост #{i}{' [→ СТРИМ]' if is_live else ''}{RESET}")
            print(f"     Текст: {text[:250]}{'...' if len(text) > 250 else ''}")
            if stream_links:
                print(f"     {GREEN}Ссылки на платформы: {stream_links}{RESET}")
            if found_kw:
                print(f"     {GREEN}Ключевые слова: {found_kw}{RESET}")
            if not found_kw and not stream_links:
                print(f"     {YELLOW}(ничего не найдено){RESET}")
        print(f"\n  Итог: {mark(any_live)}")
    except Exception as e:
        print(f"  {RED}Ошибка: {e}{RESET}")


# ── VK группа ─────────────────────────────────────────────────

def test_vk_group(url):
    domain = slug(url)
    if not domain:
        print(f"  {RED}URL пустой{RESET}"); return
    print(f"  Группа: vk.com/{domain}")
    token = config.VK_SERVICE_TOKEN
    if not token or "СЮДА" in token:
        print(f"  {YELLOW}⚠ VK_SERVICE_TOKEN не заполнен в config.py — пропускаю{RESET}")
        return
    try:
        r = requests.get("https://api.vk.com/method/wall.get", params={
            "domain": domain, "count": 5,
            "access_token": token, "v": "5.199",
        }, timeout=10)
        data = r.json()
        if "error" in data:
            print(f"  {RED}VK API ошибка: {data['error']['error_msg']}{RESET}")
            return
        items = data.get("response", {}).get("items", [])
        if not items:
            print(f"  {YELLOW}⚠ Постов не найдено{RESET}"); return
        print(f"  Найдено постов: {len(items)}\n")
        any_live = False
        for i, post in enumerate(items, 1):
            text = post.get("text", "")
            attachments = post.get("attachments", [])
            attach_links = [a.get("link", {}).get("url", "") for a in attachments if a.get("type") == "link"]
            inline_links = re.findall(r'https?://\S+', text)
            all_links = attach_links + inline_links
            stream_links = [l for l in all_links if any(d in l for d in config.STREAM_LINK_DOMAINS)]
            full = text + " " + " ".join(all_links)
            found_kw, found_links, is_live = check_keywords(full)
            any_live = any_live or is_live
            print(f"  {CYAN}── Пост #{i}{' [→ СТРИМ]' if is_live else ''}{RESET}")
            print(f"     Текст: {text[:250].strip() or '(без текста)'}{'...' if len(text) > 250 else ''}")
            if stream_links:
                print(f"     {GREEN}Ссылки на платформы: {stream_links}{RESET}")
            if found_kw:
                print(f"     {GREEN}Ключевые слова: {found_kw}{RESET}")
            if not found_kw and not stream_links:
                print(f"     {YELLOW}(ничего не найдено){RESET}")
        print(f"\n  Итог: {mark(any_live)}")
    except Exception as e:
        print(f"  {RED}Ошибка: {e}{RESET}")


# ── Twitch ────────────────────────────────────────────────────

def test_twitch(url):
    login = slug(url)
    if not login:
        print(f"  {RED}URL пустой{RESET}"); return
    print(f"  Логин: {login}")
    if config.TWITCH_CLIENT_ID and config.TWITCH_CLIENT_SECRET:
        try:
            tok = S.post("https://id.twitch.tv/oauth2/token", params={
                "client_id": config.TWITCH_CLIENT_ID,
                "client_secret": config.TWITCH_CLIENT_SECRET,
                "grant_type": "client_credentials",
            }, timeout=10).json().get("access_token")
            r = S.get("https://api.twitch.tv/helix/streams",
                      params={"user_login": login},
                      headers={"Client-ID": config.TWITCH_CLIENT_ID,
                               "Authorization": f"Bearer {tok}"},
                      timeout=10)
            data = r.json().get("data", [])
            print(f"  Метод: Twitch API")
            if data:
                print(f"  {GREEN}Стрим: {data[0].get('title','')} / {data[0].get('game_name','')}{RESET}")
            print(f"  Итог: {mark(bool(data))}")
            return
        except Exception as e:
            print(f"  {YELLOW}Twitch API не сработал: {e}{RESET}")
    try:
        r = S.get(url, timeout=15)
        live = "isLiveBroadcast" in r.text or "В ЭФИРЕ" in r.text
        print(f"  Метод: HTML парсинг")
        print(f"  {YELLOW}⚠ Без API ключей Twitch может блокировать запросы{RESET}")
        print(f"  Итог: {mark(live)}")
    except Exception as e:
        print(f"  {RED}Ошибка: {e}{RESET}")


# ── YouTube ───────────────────────────────────────────────────

def test_youtube(url):
    if not url:
        print(f"  {RED}URL пустой{RESET}"); return
    live_url = url if url.endswith("/live") else url.rstrip("/") + "/live"
    print(f"  URL: {live_url}")
    if config.YOUTUBE_API_KEY:
        path = urlparse(url).path.strip("/").split("/")
        ch_id = next((p for p in path if p.startswith("@") or p.startswith("UC")), path[-1])
        try:
            r = S.get("https://www.googleapis.com/youtube/v3/search", params={
                "part": "snippet", "channelId": ch_id,
                "eventType": "live", "type": "video",
                "key": config.YOUTUBE_API_KEY,
            }, timeout=10)
            items = r.json().get("items", [])
            print(f"  Метод: YouTube API")
            if items:
                print(f"  {GREEN}Стрим: {items[0]['snippet'].get('title','')}{RESET}")
            print(f"  Итог: {mark(bool(items))}")
            return
        except Exception as e:
            print(f"  {YELLOW}YouTube API не сработал: {e}{RESET}")
    try:
        r = S.get(live_url, timeout=15)
        live = ('"liveBroadcastContent":"live"' in r.text or
                "isLiveBroadcast" in r.text or "ЭФИР" in r.text)
        print(f"  Метод: HTML парсинг")
        print(f"  Итог: {mark(live)}")
    except Exception as e:
        print(f"  {RED}Ошибка: {e}{RESET}")


# ── Kick ──────────────────────────────────────────────────────

def test_kick(url):
    login = slug(url)
    if not login:
        print(f"  {RED}URL пустой{RESET}"); return
    print(f"  Логин: {login}")
    try:
        r = S.get(f"https://kick.com/api/v1/channels/{login}", timeout=15)
        ls = r.json().get("livestream")
        print(f"  Метод: Kick API")
        if ls:
            print(f"  {GREEN}Стрим: {ls.get('session_title','')}{RESET}")
        print(f"  Итог: {mark(bool(ls))}")
    except Exception as e:
        print(f"  {RED}Ошибка: {e}{RESET}")


# ── VK Play Live ──────────────────────────────────────────────
# ИСПРАВЛЕНО: обработка ответа-списка

def test_vkplay(url):
    login = slug(url)
    if not login:
        print(f"  {RED}URL пустой{RESET}"); return
    print(f"  Логин: {login}")
    try:
        r = S.get(f"https://api.vkplay.live/v1/blog/{login}/public_video_stream", timeout=15)
        data = r.json()
        print(f"  Тип ответа API: {type(data).__name__}")

        if isinstance(data, list):
            online = any(
                item.get("isOnline") or item.get("data", {}).get("isOnline")
                for item in data if isinstance(item, dict)
            )
            title = next(
                (item.get("title","") or item.get("data",{}).get("title","")
                 for item in data if isinstance(item, dict)
                 if item.get("isOnline") or item.get("data",{}).get("isOnline")),
                ""
            )
        else:
            online = bool(data.get("data", {}).get("isOnline"))
            title  = data.get("data", {}).get("title", "")

        if online:
            print(f"  {GREEN}Стрим: {title}{RESET}")
        print(f"  Итог: {mark(online)}")
    except Exception as e:
        print(f"  {RED}Ошибка: {e}{RESET}")


# ── Главный запуск ────────────────────────────────────────────

TESTS = [
    ("twitch",   "🟣 Twitch",       test_twitch),
    ("youtube",  "🔴 YouTube",      test_youtube),
    ("kick",     "🟢 Kick",         test_kick),
    ("vkplay",   "🔵 VK Play Live", test_vkplay),
    ("telegram", "✈️  Telegram",    test_telegram),
    ("vk_group", "💙 Группа ВК",   test_vk_group),
]

def run():
    print(f"\n{BOLD}{'═'*60}")
    print(f"  РУЧНАЯ ПРОВЕРКА ВСЕХ ИСТОЧНИКОВ")
    print(f"{'═'*60}{RESET}")
    print(f"  Ключевые слова: {sorted(config.STREAM_KEYWORDS)}")
    print(f"  Мин. совпадений: {config.KEYWORD_MIN_MATCHES}")
    print(f"  Домены-триггеры: {config.STREAM_LINK_DOMAINS}\n")

    for streamer in config.STREAMERS:
        print(f"\n{BOLD}╔{'═'*58}╗")
        print(f"  СТРИМЕР: {streamer['name']}  (id: {streamer['id']})")
        print(f"╚{'═'*58}╝{RESET}")

        for key, label, fn in TESTS:
            url = streamer.get(key, "")
            if not url:
                continue
            print(f"\n{BOLD}  {label}{RESET}")
            print(f"  URL: {url}")
            print(SEP)
            fn(url)

    print(f"\n{BOLD}{'═'*60}")
    print(f"  ПРОВЕРКА ЗАВЕРШЕНА")
    print(f"{'═'*60}{RESET}\n")

if __name__ == "__main__":
    run()
