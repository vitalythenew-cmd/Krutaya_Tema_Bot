"""
Крутая Тема — Telegram Bot (исправленная версия, сентябрь 2026)
================================================================
Использует новый Google GenAI SDK который работает с AQ. ключами.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timezone
from google import genai

# ── Настройки ────────────────────────────────────────────────
GEMINI_API_KEY       = os.environ["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL_ID  = os.environ["TELEGRAM_CHANNEL_ID"]
MY_TELEGRAM_USER_ID  = int(os.environ["MY_TELEGRAM_USER_ID"])

TG = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
STATE_FILE = "today_draft.json"

# ── Темы постов ──────────────────────────────────────────────
TOPICS = [
    "удивительный факт о простых числах",
    "парадокс или загадка, которая взрывает мозг",
    "скрытая математика в повседневной жизни (музыка, природа, спорт, дизайн)",
    "красивое математическое доказательство, понятное любому",
    "история знаменитого математика — как захватывающий детектив",
    "математический фокус или трюк для быстрого счёта в уме",
    "как геометрия или математика прячется в кино, архитектуре или искусстве",
    "контринтуитивный результат из теории вероятностей (например, парадокс дней рождения)",
    "математика за популярной игрой или вирусной темой в интернете",
    "нерешённая математическая задача — то, с чем не справились даже гении",
    "золотое сечение и где оно тайно встречается вокруг нас",
    "бесконечность: почему одни бесконечности больше других",
    "число π: факты, которых ты не знал",
    "теория игр: как математика объясняет поведение людей",
    "топология: математика, которая объясняет форму вселенной",
]

def pick_topic():
    day = datetime.now(timezone.utc).timetuple().tm_yday
    return TOPICS[day % len(TOPICS)]


# ── ФАЗА 1А: Генерация поста через новый Gemini SDK ─────────

def generate_post():
    topic = pick_topic()
    today = datetime.now(timezone.utc).strftime("%d %B %Y")

    prompt = f"""Ты — автор Telegram-канала «Крутая Тема» о математике.
Твоя аудитория: молодые люди 16–30 лет, любопытные, но не математики-профессионалы.
Сегодня: {today}. Тема поста: {topic}.

Напиши ОДИН пост для Telegram. Правила:
- Максимум 280 слов
- Начни с крючка: смелое утверждение, неожиданный факт или вопрос
- Разговорный стиль — как умный друг объясняет что-то классное
- 1–2 эмодзи, органично вписанные в текст
- Заверши вопросом или вызовом для читателя
- Без заголовков, без списков с точками — чистые абзацы
- Последняя строка: 3–5 хэштегов (например: #математика #крутаятема #учисьинтересно)
- Пиши на живом, современном русском языке.

Выведи только текст поста. Никаких предисловий."""

    # Новый способ вызова — через официальный SDK (работает с AQ. ключами)
    client = genai.Client(api_key=GEMINI_API_KEY)

    for attempt in range(3):
        try:
            print(f"🌐 Попытка {attempt + 1}/3...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text.strip()
            print("✅ Gemini ответил успешно.")
            return text, topic
        except Exception as e:
            print(f"⚠️  Ошибка на попытке {attempt + 1}: {e}")
            if attempt < 2:
                wait = 15 + attempt * 15
                print(f"⏳ Жду {wait} секунд...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Gemini недоступен после 3 попыток: {e}")


# ── ФАЗА 1Б: Отправить черновик тебе в Telegram ─────────────

def send_draft_to_me(post_text, topic):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    message = (
        f"📋 <b>Крутая Тема — черновик {today}</b>\n"
        f"Тема: <i>{topic}</i>\n\n"
        f"{'─' * 30}\n"
        f"{post_text}\n"
        f"{'─' * 30}\n\n"
        f"Ответь:\n"
        f"• <b>YES</b> → опубликую именно это\n"
        f"• <b>SKIP</b> → пропустить сегодня\n"
        f"• <i>Любой другой текст</i> → опубликую твою версию"
    )
    r = requests.post(
        f"{TG}/sendMessage",
        json={"chat_id": MY_TELEGRAM_USER_ID, "text": message, "parse_mode": "HTML"},
        timeout=20
    )
    r.raise_for_status()
    print(f"✅ Черновик отправлен тебе в Telegram.")


# ── ФАЗА 1В: Сохранить черновик ─────────────────────────────

def save_draft(post_text, topic):
    state = {
        "date":  datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topic": topic,
        "post":  post_text,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("💾 Черновик сохранён.")

def load_draft():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if state.get("date") == today:
            return state["post"], state["topic"]
        print("⚠️  Черновик устарел.")
        return None, None
    except FileNotFoundError:
        print("⚠️  Файл черновика не найден.")
        return None, None


# ── ФАЗА 2А: Проверить твой ответ в Telegram ────────────────

def check_my_reply():
    r = requests.get(f"{TG}/getUpdates", params={"limit": 100}, timeout=20)
    r.raise_for_status()
    updates = r.json().get("result", [])

    now_ts = datetime.now(timezone.utc).timestamp()
    WINDOW = 3.5 * 60 * 60

    for update in reversed(updates):
        msg = update.get("message")
        if not msg:
            continue
        sender_id = msg.get("from", {}).get("id")
        if sender_id != MY_TELEGRAM_USER_ID:
            continue
        msg_ts = msg.get("date", 0)
        if now_ts - msg_ts > WINDOW:
            continue
        text = msg.get("text", "").strip()
        if not text:
            continue
        first_word = text.split()[0].upper()
        if first_word == "YES":
            print("✅ Одобрено: YES")
            return "YES"
        if first_word == "SKIP":
            print("⏭️  Команда: SKIP")
            return "SKIP"
        print(f"✏️  Получены правки ({len(text)} символов)")
        return text

    print("❌ Ответ не найден за последние 3.5 часа.")
    return None


# ── ФАЗА 2Б: Опубликовать в канал ───────────────────────────

def post_to_channel(text):
    r = requests.post(
        f"{TG}/sendMessage",
        json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text, "parse_mode": "HTML"},
        timeout=20
    )
    r.raise_for_status()
    print(f"🚀 Опубликовано в канал!")


# ── ЗАПУСК ───────────────────────────────────────────────────

def run_generate():
    print("🔮 Генерирую пост через Gemini...")
    post_text, topic = generate_post()
    print(f"\n--- ЧЕРНОВИК ---\n{post_text}\n---\n")
    save_draft(post_text, topic)
    print("📲 Отправляю черновик тебе в Telegram...")
    send_draft_to_me(post_text, topic)
    print("✅ Фаза 1 завершена. Жду твоего ответа в Telegram.")

def run_post():
    print("🔍 Проверяю твой ответ в Telegram...")
    reply = check_my_reply()
    if reply is None:
        print("Ответа нет. Пост пропущен.")
        return
    if reply == "SKIP":
        print("Пропускаю.")
        return
    post_text, topic = load_draft()
    if post_text is None:
        print("❌ Не могу загрузить черновик. Отмена.")
        return
    final_text = post_text if reply == "YES" else reply
    print("🚀 Публикую в канал...")
    post_to_channel(final_text)
    print("✅ Пост опубликован!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python bot.py [generate|post]")
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "generate":
        run_generate()
    elif cmd == "post":
        run_post()
    else:
        print(f"Неизвестная команда: {cmd}")
        sys.exit(1)
