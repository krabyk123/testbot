"""
test_notify.py — проверка отправки уведомлений.
Отправляет тестовое сообщение указанному пользователю.

Запуск: python test_notify.py
"""
import time
import vk_api
import config

vk_session = vk_api.VkApi(token=config.VK_TOKEN)
vk = vk_session.get_api()

# ← Вставь сюда свой VK user ID
# Где найти: vk.com/id??? — число в URL твоей страницы
MY_USER_ID = 427099655

test_message = (
    "🔴 ТЕСТ — HARD PLAY в эфире!\n"
    "🟣 Twitch: https://twitch.tv/hardgamechannel\n\n"
    "Если ты это видишь — уведомления работают ✅"
)

try:
    vk.messages.send(
        user_id=MY_USER_ID,
        message=test_message,
        random_id=int(time.time()),
    )
    print("✅ Сообщение отправлено! Проверь ВК.")
except Exception as e:
    print(f"❌ Ошибка: {e}")
