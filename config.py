# ================================================================
# config.py — ВСЕ настройки бота. Заполни отмеченные строки.
# ================================================================
#
#  ЧТО НУЖНО ЗАПОЛНИТЬ ОБЯЗАТЕЛЬНО:
#    1. VK_TOKEN         — токен ВАШЕЙ группы-бота
#    2. VK_GROUP_ID      — ID ВАШЕЙ группы-бота
#    3. VK_SERVICE_TOKEN — сервисный ключ (для чтения групп стримеров)
#    4. STREAMERS        — ссылки на стримеров
#
#  ЧТО ОПЦИОНАЛЬНО (но рекомендуется):
#    5. TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET
#    6. YOUTUBE_API_KEY
#
# ================================================================


# ── 1. Токен ВАШЕЙ группы-бота ─────────────────────────────────
# Где взять: vk.com → Ваша группа → Управление → Работа с API
#            → Ключи доступа → Создать ключ
#            Права: ✅ Сообщения, ✅ Управление
VK_TOKEN = "СЮДА_ТОКЕН_ВАШЕЙ_ГРУППЫ_БОТА"

# ── 2. ID ВАШЕЙ группы-бота ────────────────────────────────────
# Где взять: открой страницу группы → в URL: vk.com/clubЧИСЛО
# Или: Управление → Работа с API — там написан ID
VK_GROUP_ID = 0  # ← замени на число, например: 236231799

# ── 3. Сервисный ключ ВК ───────────────────────────────────────
# Нужен чтобы читать стены ЧУЖИХ публичных групп (стримеров).
# Группа-токен это не умеет — нужен именно сервисный ключ.
#
# Где взять:
#   1. vk.com/dev → «Мои приложения» → «Создать приложение»
#   2. Тип: Мини-приложение, название любое → «Подключить»
#   3. Слева «Настройки» → строка «Сервисный ключ доступа» → скопировать
VK_SERVICE_TOKEN = "СЮДА_СЕРВИСНЫЙ_КЛЮЧ_VK"


# ── 4. Список стримеров ────────────────────────────────────────
# Вставляй публичные ссылки. Что не нужно — оставь "".
# Бот извлечёт логины из URL сам.
STREAMERS = [
    {
        "id":       "hardplay",          # латиница без пробелов, уникальный
        "name":     "HARD PLAY",         # имя в уведомлениях и кнопках
        "twitch":   "https://twitch.tv/hardgamechannel",
        "youtube":  "https://www.youtube.com/@hardplayyt/live",
        "kick":     "https://kick.com/hardplayofficial",
        "vkplay":   "https://live.vkvideo.ru/hardplay",
        "telegram": "https://t.me/hplegion",
        "vk_group": "https://vk.com/hp_legion",
    },

    # Шаблон для нового стримера — раскомментируй и заполни:
    # {
    #     "id":       "streamer2",
    #     "name":     "Имя Стримера",
    #     "twitch":   "https://twitch.tv/LOGIN",
    #     "youtube":  "https://www.youtube.com/@HANDLE/live",
    #     "kick":     "https://kick.com/LOGIN",
    #     "vkplay":   "https://live.vkvideo.ru/LOGIN",
    #     "telegram": "https://t.me/CHANNEL",
    #     "vk_group": "https://vk.com/GROUP",
    # },
]


# ── 5. Twitch API (рекомендуется!) ─────────────────────────────
# Без ключей Cloudflare блокирует HTML-парсинг Twitch.
# Получить бесплатно (1 минута):
#   1. https://dev.twitch.tv/console/apps → Register Your Application
#   2. Name: любое | OAuth Redirect URLs: http://localhost | Category: любая
#   3. Скопировать Client ID и сгенерировать Client Secret
TWITCH_CLIENT_ID     = ""   # ← вставь сюда
TWITCH_CLIENT_SECRET = ""   # ← вставь сюда


# ── 6. YouTube API (рекомендуется!) ────────────────────────────
# Получить бесплатно:
#   1. https://console.cloud.google.com → создай проект
#   2. APIs & Services → Enable APIs → YouTube Data API v3 → включить
#   3. Credentials → Create Credentials → API Key → скопировать
YOUTUBE_API_KEY = ""   # ← вставь сюда


# ── Настройки проверки ─────────────────────────────────────────
CHECK_INTERVAL_SECONDS = 60

KEYWORD_MIN_MATCHES = 1   # 1 = достаточно одного слова (оптимально для коротких постов)

STREAM_KEYWORDS = {
    "стрим", "stream", "live", "лайв", "эфир", "трансляция",
    "начал", "стримим", "в эфире", "онлайн стрим", "смотрите",
}

STREAM_LINK_DOMAINS = [
    "twitch.tv",
    "youtube.com/watch",
    "youtube.com/live",      # ← ИСПРАВЛЕНИЕ: ловит ссылки youtube.com/live/...
    "youtu.be",
    "kick.com",
    "vkplay.live",
    "live.vkvideo.ru",       # ← ИСПРАВЛЕНИЕ: новый домен VK Play Live
]


# ── Тексты сообщений ───────────────────────────────────────────
MSG_WELCOME = (
    "👋 Привет! Я бот уведомлений о стримах.\n\n"
    "Выбери стримеров, о которых хочешь получать уведомления.\n"
    "Нажми на имя — подписка включится/выключится.\n\n"
    "✅ — подписан  |  ➕ — не подписан"
)
MSG_SUBSCRIBED   = "✅ Подписка на {name} включена!"
MSG_UNSUBSCRIBED = "❌ Подписка на {name} отключена."
MSG_NO_SUBS      = "У тебя пока нет подписок. Нажми /start чтобы выбрать стримеров."
MSG_LIVE         = "🔴 {name} в эфире!\n{platform_icon} {platform_name}: {url}"
