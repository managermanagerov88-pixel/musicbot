import logging
import sqlite3
import requests
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# =====================================
# CONFIG
# =====================================

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL_USERNAME = "@sp_rap"
ADMIN_ID = 1125040535

# =====================================
# INIT
# =====================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =====================================
# DATABASE
# =====================================

conn = sqlite3.connect("musicbot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    time TEXT
)
""")

conn.commit()

# =====================================
# MENU
# =====================================

menu = ReplyKeyboardMarkup(resize_keyboard=True)

menu.add(
    KeyboardButton("🎵 Как пользоваться"),
    KeyboardButton("📊 Статус")
)

# =====================================
# CHECK SUB
# =====================================

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "creator", "administrator"]:
            return True

        return False

    except:
        return False

# =====================================
# START
# =====================================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    sub = await check_sub(message.from_user.id)

    if not sub:

        kb = InlineKeyboardMarkup()

        kb.add(
            InlineKeyboardButton(
                "📢 Подписаться",
                url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
            )
        )

        await message.answer(
            "❗ Для использования бота подпишись на канал",
            reply_markup=kb
        )

        return

    cursor.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
        (
            message.from_user.id,
            message.from_user.username,
            str(datetime.now())
        )
    )

    conn.commit()

    text = """
🎧 SPACE SEARCH

Поиск музыки по:
• Голосовым
• Кружкам
• Видео
• Отрывкам текста

━━━━━━━━━━━━━━

📌 Как пользоваться:

1. Отправь:
• голосовое
• кружок
• видео
• текст из песни

2. Бот найдёт:
• название трека
• исполнителя
• обложку

3. Ты получишь ссылки:
• Spotify
• Яндекс Музыка
• YouTube
• Genius

━━━━━━━━━━━━━━

🔥 Просто отправь сообщение с музыкой
"""

    await message.answer(text, reply_markup=menu)

# =====================================
# HELP
# =====================================

@dp.message_handler(lambda m: m.text == "🎵 Как пользоваться")
async def help_handler(message: types.Message):

    text = """
📖 ИНСТРУКЦИЯ

Бот умеет искать музыку по:

🎤 Голосовым
🎥 Видео
⭕ Кружкам
📝 Тексту песни

━━━━━━━━━━━━━━

📌 Примеры:

• отправь кружок из TikTok
• отправь видео
• отправь голосовое
• отправь строчку песни

━━━━━━━━━━━━━━

После поиска бот отправит:

✅ Название
✅ Исполнителя
✅ Обложку
✅ Spotify
✅ YouTube
✅ Яндекс Музыка
✅ Genius

━━━━━━━━━━━━━━

🔥 Просто отправь любой медиафайл
"""

    await message.answer(text)

# =====================================
# STATUS
# =====================================

@dp.message_handler(lambda m: m.text == "📊 Статус")
async def status_handler(message: types.Message):

    await message.answer(
        "🟢 Бот работает стабильно"
    )

# =====================================
# COVER
# =====================================

def get_cover(artist, title):

    try:

        query = f"{artist} {title}"

        r = requests.get(
            "https://itunes.apple.com/search",
            params={
                "term": query,
                "entity": "song",
                "limit": 10
            },
            timeout=15
        ).json()

        results = r.get("results")

        if not results:
            return None

        artist_lower = artist.lower()
        title_lower = title.lower()

        best_score = -1
        best_cover = None

        for item in results:

            item_artist = item.get(
                "artistName",
                ""
            ).lower()

            item_title = item.get(
                "trackName",
                ""
            ).lower()

            score = 0

            # точный артист
            if artist_lower == item_artist:
                score += 100

            elif artist_lower in item_artist:
                score += 50

            # точное название
            if title_lower == item_title:
                score += 100

            elif title_lower in item_title:
                score += 50

            # фильтр мусора

            banned = [
                "remix",
                "live",
                "karaoke",
                "instrumental",
                "slowed",
                "speed up",
                "nightcore"
            ]

            bad = False

            for b in banned:

                if b in item_title:
                    bad = True
                    break

            if bad:
                continue

            if score > best_score:

                best_score = score

                best_cover = item.get(
                    "artworkUrl100"
                )

        if best_cover:

            return best_cover.replace(
                "100x100",
                "1200x1200"
            )

        return None

    except Exception as e:

        print(e)

        return None

    try:

        r = requests.get(
            "https://itunes.apple.com/search",
            params={
                "term": f"{artist} {title}",
                "limit": 5
            }
        ).json()

        results = r.get("results")

        if not results:
            return None

        for item in results:

            if item.get("artworkUrl100"):

                return item["artworkUrl100"].replace(
                    "100x100",
                    "600x600"
                )

        return None

    except:
        return None

# =====================================
# LINKS
# =====================================

def get_links(artist, title):

    query = f"{artist} {title}"

    return {
        "spotify":
        f"https://open.spotify.com/search/{query}",

        "youtube":
        f"https://youtube.com/results?search_query={query}",

        "yandex":
        f"https://music.yandex.ru/search?text={query}",

        "genius":
        f"https://genius.com/search?q={query}"
    }

# =====================================
# SEARCH
# =====================================

async def process_music(message, file_url, search_type):

    wait = await message.answer("🔎 Ищу трек...")

    try:

        response = requests.post(
            "https://api.audd.io/",
            data={
                "api_token": AUDD_API_KEY,
                "url": file_url
            },
            timeout=40
        ).json()

        result = response.get("result")

        if not result:

            await wait.edit_text(
                "❌ Трек не найден"
            )

            return

        artist = result.get("artist", "Unknown")
        title = result.get("title", "Unknown")

        # stats

        cursor.execute(
            "INSERT INTO searches (user_id, type, time) VALUES (?, ?, ?)",
            (
                message.from_user.id,
                search_type,
                str(datetime.now())
            )
        )

        conn.commit()

        # links

        links = get_links(artist, title)

        kb = InlineKeyboardMarkup(row_width=2)

        kb.add(
            InlineKeyboardButton(
                "🎧 Spotify",
                url=links["spotify"]
            ),

            InlineKeyboardButton(
                "▶ YouTube",
                url=links["youtube"]
            )
        )

        kb.add(
            InlineKeyboardButton(
                "🎵 Яндекс",
                url=links["yandex"]
            ),

            InlineKeyboardButton(
                "📜 Genius",
                url=links["genius"]
            )
        )

        # cover

        cover = get_cover(artist, title)

        text = f"""
🎵 {artist} — {title}

━━━━━━━━━━━━━━

✅ Трек успешно найден
"""

        if cover:

            await bot.send_photo(
                message.chat.id,
                cover,
                caption=text,
                reply_markup=kb
            )

        else:

            await message.answer(
                text,
                reply_markup=kb
            )

        await wait.delete()

    except Exception as e:

        print(e)

        await wait.edit_text(
            "❌ Ошибка поиска"
        )

# =====================================
# VOICE
# =====================================

@dp.message_handler(content_types=["voice"])
async def voice_handler(message: types.Message):

    file = await bot.get_file(message.voice.file_id)

    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    await process_music(message, file_url, "voice")

# =====================================
# VIDEO NOTE
# =====================================

@dp.message_handler(content_types=["video_note"])
async def circle_handler(message: types.Message):

    file = await bot.get_file(message.video_note.file_id)

    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    await process_music(message, file_url, "circle")

# =====================================
# VIDEO
# =====================================

@dp.message_handler(content_types=["video"])
async def video_handler(message: types.Message):

    file = await bot.get_file(message.video.file_id)

    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    await process_music(message, file_url, "video")

# =====================================
# TEXT SEARCH
# =====================================

@dp.message_handler(content_types=["text"])
async def text_search(message: types.Message):

    if message.text in [
        "🎵 Как пользоваться",
        "📊 Статус"
    ]:
        return

    if message.text.startswith("/"):
        return

    wait = await message.answer(
        "🔎 Ищу трек..."
    )

    try:

        r = requests.get(
            "https://api.lyrics.ovh/suggest/" + message.text,
            timeout=15
        ).json()

        data = r.get("data")

        if not data:

            await wait.edit_text(
                "❌ Ничего не найдено"
            )

            return

        first = data[0]

        artist = first["artist"]["name"]
        title = first["title"]

        cursor.execute(
            "INSERT INTO searches (user_id, type, time) VALUES (?, ?, ?)",
            (
                message.from_user.id,
                "text",
                str(datetime.now())
            )
        )

        conn.commit()

        links = get_links(artist, title)

        kb = InlineKeyboardMarkup(row_width=2)

        kb.add(
            InlineKeyboardButton(
                "🎧 Spotify",
                url=links["spotify"]
            ),

            InlineKeyboardButton(
                "▶ YouTube",
                url=links["youtube"]
            )
        )

        kb.add(
            InlineKeyboardButton(
                "🎵 Яндекс",
                url=links["yandex"]
            ),

            InlineKeyboardButton(
                "📜 Genius",
                url=links["genius"]
            )
        )

        cover = get_cover(artist, title)

        text = f"""
🎵 {artist} — {title}

━━━━━━━━━━━━━━

✅ Трек найден по тексту
"""

        if cover:

            await bot.send_photo(
                message.chat.id,
                cover,
                caption=text,
                reply_markup=kb
            )

        else:

            await message.answer(
                text,
                reply_markup=kb
            )

        await wait.delete()

    except:

        await wait.edit_text(
            "❌ Ошибка поиска"
        )

# =====================================
# ADMIN
# =====================================

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cursor.fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT COUNT(*) FROM searches WHERE time LIKE ?",
        (f"{today}%",)
    )

    today_searches = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM searches"
    )

    all_searches = cursor.fetchone()[0]

    cursor.execute("""
    SELECT type, COUNT(*)
    FROM searches
    GROUP BY type
    """)

    stats = cursor.fetchall()

    stat_text = ""

    for s in stats:
        stat_text += f"{s[0]}: {s[1]}\n"

    text = f"""
🛠 ADMIN PANEL

━━━━━━━━━━━━━━

👤 Пользователей: {users}

🔎 Всего поисков: {all_searches}

📅 Поисков сегодня: {today_searches}

━━━━━━━━━━━━━━

📊 Типы поисков:

{stat_text}
"""

    await message.answer(text)

# =====================================
# RUN
# =====================================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)