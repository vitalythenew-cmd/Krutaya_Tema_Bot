"""
Крутая Тема — Telegram Bot с картинками (сентябрь 2026)
========================================================
Генерирует пост через Gemini, находит картинку на Pixabay,
присылает тебе на проверку, публикует в канал с картинкой.
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
PIXABAY_API_KEY      = os.environ["PIXABAY_API_KEY"]

TG = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
STATE_FILE = "today_draft.json"

# ── Темы постов ──────────────────────────────────────────────
TOPICS = [
    ("удивительный факт о простых числах", "prime numbers mathematics"),
    ("парадокс или загадка, которая взрывает мозг", "mathematics puzzle brain"),
    ("скрытая математика в повседневной жизни", "mathematics nature geometry"),
    ("красивое математическое доказательство", "mathematics abstract art"),
    ("история знаменитого математика", "scientist genius blackboard"),
    ("математический фокус или трюк для счёта в уме", "mathematics numbers magic"),
    ("как геометрия прячется в архитектуре", "geometry architecture pattern"),
    ("контринтуитивный результат из теории вероятностей", "probability statistics data"),
    ("математика за популярной игрой", "game strategy mathematics"),
    ("нерешённая математическая задача", "mathematics infinity abstract"),
    ("золотое сечение и где оно встречается", "golden ratio spiral nature"),
    ("бесконечность: почему одни бесконечности больше других", "infinity universe space"),
    ("число π: факты, которых ты не знал", "pi circle mathematics"),
    ("теория игр: математика поведения людей", "chess strategy game theory"),
    ("топология: математика формы вселенной", "topology mathematics shape"),
]

def pick_topic():
    day = datetime.now(timezone.utc).timetuple().tm_yday
    return TOPICS[day % len(TOPICS)]


# ── ФАЗА 1А: Генерация поста через Gemini ───────────────────

def generate_post():
    topic_ru, topic_en = pick_topic()
    today = datetime.now(timezone.utc).strftime("%d %B %Y")

    prompt = f"""Ты — автор Telegram-канала «Крутая Тема» о математике.
Твоя аудитория: молодые люди 16–30 лет, любопытные, но не математики-профессионалы.
Сегодня: {today}. Тема поста: {topic_ru}.

Напиши ОДИН пост для Telegram. Правила:
- Максимум 280 слов
- Начни с крючка: смелое утверждение, неожиданный факт или вопрос
- Разговорный стиль — как умный друг объясняет что-то классное
- 1–2 эмодзи, органично вписанные в текст
- Заверши вопросом или вызовом для читателя
- Без заголовков, без списков с точками — чистые абзацы
- Последняя строка: 3–5 хэштегов
- Пиши на живом, современном русском языке.

Выведи только текст поста. Никаких предисловий."""

    client = genai.Client(api_key=GEMINI_API_KEY)

    for attempt in range(3):
        try:
            print(f"🌐 Попытка {attempt + 1}/3...")
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
            text = response.text.strip()
            print("✅ Gemini ответил успешно.")
            return text, topic_ru, topic_en
        except Exception as e:
            print(f"⚠️  Ошибка на попытке {attempt + 1}: {e}")
            if attempt < 2:
                wait = 15 + attempt * 15
                print(f"⏳ Жду {wait} секунд...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Gemini недоступен после 3 попыток: {e}")


# ── ФАЗА 1Б: Найти картинку на Pixabay ──────────────────────

def find_image(search_query_en):
    """Ищет подходящую картинку на Pixabay по английскому запросу."""
    print(f"🖼️  Ищу картинку: '{search_query_en}'...")
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key":        PIXABAY_API_KEY,
                "q":          search_query_en,
                "image_type": "photo",
                "category":   "science",
                "safesearch": "true",
                "per_page":   10,
                "order":      "popular",
            },
            timeout=15
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])

        if not hits:
            # Попробуем без категории если ничего не нашли
            r2 = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key":        PIXABAY_API_KEY,
                    "q":          search_query_en,
                    "image_type": "photo",
                    "safesearch": "true",
                    "per_page":   10,
                },
                timeout=15
            )
            hits = r2.json().get("hits", [])

        if hits:
            image_url = hits[0]["webformatURL"]
            print(f"✅ Картинка найдена!")
            return image_url
        else:
            print("⚠️  Картинка не найдена, пост будет без картинки.")
            return None

    except Exception as e:
        print(f"⚠️  Ошибка поиска картинки: {e}. Пост будет без картинки.")
        return None


# ── ФАЗА 1В: Отправить черновик тебе в Telegram ─────────────

def send_draft_to_me(post_text, topic_ru, image_url):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    caption = (
        f"📋 <b>Крутая Тема — черновик {today}</b>\n"
        f"Тема: <i>{topic_ru}</i>\n\n"
        f"{'─' * 30}\n"
        f"{post_text}\n"
        f"{'─' * 30}\n\n"
        f"Ответь:\n"
        f"• <b>YES</b> → опубликую именно это\n"
        f"• <b>SKIP</b> → пропустить сегодня\n"
        f"• <i>Любой другой текст</i> → опубликую твою версию"
    )

    if image_url:
        try:
            # Скачиваем картинку и отправляем как файл
            img_data = requests.get(image_url, timeout=15).content
            r = requests.post(
                f"{TG}/sendPhoto",
                data={"chat_id": MY_TELEGRAM_USER_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("image.jpg", img_data, "image/jpeg")},
                timeout=30
            )
            r.raise_for_status()
        except Exception as e:
            print(f"⚠️  Не удалось отправить фото: {e}. Отправляю без картинки.")
            r = requests.post(
                f"{TG}/sendMessage",
                json={"chat_id": MY_TELEGRAM_USER_ID, "text": caption, "parse_mode": "HTML"},
                timeout=20
            )
            r.raise_for_status()
    else:
        r = requests.post(
            f"{TG}/sendMessage",
            json={"chat_id": MY_TELEGRAM_USER_ID, "text": caption, "parse_mode": "HTML"},
            timeout=20
        )
        r.raise_for_status()

    print(f"✅ Черновик отправлен тебе в Telegram.")


# ── ФАЗА 1Г: Сохранить черновик ─────────────────────────────

def save_draft(post_text, topic_ru, topic_en, image_url):
    state = {
        "date":      datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topic_ru":  topic_ru,
        "topic_en":  topic_en,
        "post":      post_text,
        "image_url": image_url,
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
            return state["post"], state["topic_ru"], state.get("image_url")
        print("⚠️  Черновик устарел.")
        return None, None, None
    except FileNotFoundError:
        print("⚠️  Файл черновика не найден.")
        return None, None, None


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

def post_to_channel(text, image_url):
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            r = requests.post(
                f"{TG}/sendPhoto",
                data={"chat_id": TELEGRAM_CHANNEL_ID, "caption": text, "parse_mode": "HTML"},
                files={"photo": ("image.jpg", img_data, "image/jpeg")},
                timeout=30
            )
            r.raise_for_status()
        except Exception as e:
            print(f"⚠️  Не удалось отправить фото: {e}. Публикую без картинки.")
            r = requests.post(
                f"{TG}/sendMessage",
                json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text, "parse_mode": "HTML"},
                timeout=20
            )
            r.raise_for_status()
    else:
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
    post_text, topic_ru, topic_en = generate_post()
    print(f"\n--- ЧЕРНОВИК ---\n{post_text}\n---\n")

    image_url = find_image(topic_en)
    save_draft(post_text, topic_ru, topic_en, image_url)

    print("📲 Отправляю черновик тебе в Telegram...")
    send_draft_to_me(post_text, topic_ru, image_url)
    print("✅ Фаза 1 завершена. Жди сообщения в Telegram!")

def run_post():
    print("🔍 Проверяю твой ответ в Telegram...")
    reply = check_my_reply()

    if reply is None:
        print("Ответа нет. Пост пропущен.")
        return
    if reply == "SKIP":
        print("Пропускаю.")
        return

    post_text, topic_ru, image_url = load_draft()
    if post_text is None:
        print("❌ Не могу загрузить черновик. Отмена.")
        return

    final_text = post_text if reply == "YES" else reply
    print("🚀 Публикую в канал...")
    post_to_channel(final_text, image_url)
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
