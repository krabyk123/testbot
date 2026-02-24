"""
bot.py — главный файл. Запускать: python bot.py
"""
import logging, threading, time, json
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

import config, database as db
from checker import check_streamer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

vk_session = vk_api.VkApi(token=config.VK_TOKEN)
vk = vk_session.get_api()


def send(user_id: int, text: str, keyboard: str | None = None):
    try:
        params = dict(
            user_id=user_id,
            message=text,
            random_id=int(time.time() * 1000) % 2**31,
        )
        if keyboard:
            params["keyboard"] = keyboard
        vk.messages.send(**params)
    except Exception as e:
        log.error("send %s: %s", user_id, e)


def build_keyboard(user_id: int) -> str:
    kb = VkKeyboard(one_time=False, inline=False)
    for streamer in config.STREAMERS:
        subscribed = db.is_subscribed(user_id, streamer["id"])
        label = f"{'✅' if subscribed else '➕'} {streamer['name']}"
        kb.add_button(
            label,
            color=VkKeyboardColor.POSITIVE if subscribed else VkKeyboardColor.SECONDARY,
            payload=json.dumps({"cmd": "toggle", "sid": streamer["id"]})
        )
        kb.add_line()
    kb.add_button("📋 Мои подписки", color=VkKeyboardColor.PRIMARY,
                  payload=json.dumps({"cmd": "mysubs"}))
    kb.add_button("❌ Отписаться от всех", color=VkKeyboardColor.NEGATIVE,
                  payload=json.dumps({"cmd": "unsub_all"}))
    return kb.get_keyboard()


def handle(user_id: int, text: str, payload: dict | None):
    text = text.strip().lower()

    if payload and payload.get("cmd") == "toggle":
        sid = payload["sid"]
        streamer = next((s for s in config.STREAMERS if s["id"] == sid), None)
        if not streamer:
            return
        if db.is_subscribed(user_id, sid):
            db.unsubscribe(user_id, sid)
            msg = config.MSG_UNSUBSCRIBED.format(name=streamer["name"])
        else:
            db.subscribe(user_id, sid)
            msg = config.MSG_SUBSCRIBED.format(name=streamer["name"])
        send(user_id, msg, keyboard=build_keyboard(user_id))
        return

    if (payload and payload.get("cmd") == "mysubs") or text in ("/list", "мои подписки"):
        subs = db.get_user_subscriptions(user_id)
        if not subs:
            send(user_id, config.MSG_NO_SUBS, keyboard=build_keyboard(user_id))
        else:
            names = [s["name"] for s in config.STREAMERS if s["id"] in subs]
            send(user_id,
                 "📋 Твои подписки:\n" + "\n".join(f"• {n}" for n in names),
                 keyboard=build_keyboard(user_id))
        return

    if (payload and payload.get("cmd") == "unsub_all") or text in ("/stop", "stop", "отписаться"):
        db.unsubscribe_all(user_id)
        send(user_id, "❌ Ты отписан от всех стримеров.", keyboard=build_keyboard(user_id))
        return

    if text in ("/start", "start", "начать", "привет"):
        send(user_id, config.MSG_WELCOME, keyboard=build_keyboard(user_id))
        return

    send(user_id,
         "Используй кнопки ниже для управления подписками.\n"
         "Или напиши /start чтобы увидеть меню.",
         keyboard=build_keyboard(user_id))


# Платформы которые шлют уведомления пользователям
NOTIFY_PLATFORMS = {"twitch", "youtube", "kick", "vkplay"}

def check_loop():
    log.info("Checker started (interval=%ds)", config.CHECK_INTERVAL_SECONDS)
    while True:
        try:
            for streamer in config.STREAMERS:
                results = check_streamer(streamer)

                # Определяем — стримит ли он хоть где-то на реальных площадках
                is_streaming = any(
                    r["is_live"] for r in results
                    if r["platform"] in NOTIFY_PLATFORMS
                )

                for res in results:
                    pid  = res["platform"]
                    live = res["is_live"]
                    was  = db.get_live(streamer["id"], pid)

                    # Уведомляем только если:
                    # 1. Это реальная стрим-площадка (не TG/ВК группа)
                    # 2. Статус изменился с офлайн на онлайн
                    if pid in NOTIFY_PLATFORMS and live and not was:
                        parts = res["icon"].split(" ", 1)
                        text = config.MSG_LIVE.format(
                            name=streamer["name"],
                            platform_icon=parts[0],
                            platform_name=parts[1] if len(parts) > 1 else "",
                            url=res["url"],
                        )
                        users = db.get_subscribers_of(streamer["id"])
                        log.info("LIVE %s/%s → %d users", streamer["id"], pid, len(users))
                        for uid in users:
                            send(uid, text)

                    # Для TG и ВК группы — обновляем состояние только если
                    # не было таймаута (ошибки уже залогированы в checker.py)
                    db.set_live(streamer["id"], pid, live)

        except Exception as e:
            log.error("check_loop: %s", e)
        time.sleep(config.CHECK_INTERVAL_SECONDS)


def poll_loop():
    lp = VkLongPoll(vk_session)
    log.info("LongPoll started")
    for event in lp.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            payload = None
            try:
                raw = event.extra_values.get("payload")
                if raw:
                    payload = json.loads(raw)
            except Exception:
                pass
            handle(event.user_id, event.text or "", payload)


if __name__ == "__main__":
    db.init()
    threading.Thread(target=check_loop, daemon=True).start()
    poll_loop()
