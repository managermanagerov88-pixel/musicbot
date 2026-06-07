print("BOT STARTED")
import logging
import sqlite3
import requests
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils import executor

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL_USERNAME = "@sp_rap"
ADMIN_ID = 1125040535

# =====================================================
# INIT
# =====================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =====================================================
# DATABASE
# =====================================================

conn = sqlite3.connect("musicbot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    joined TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    search_type TEXT,
    time TEXT
)
""")

conn.commit()

# =====================================================
# MENU
# =====================================================

menu = ReplyKeyboardMarkup(
    resize_keyboard=True
)
admin_kb = InlineKeyboardMarkup()

admin_kb.add(
    InlineKeyboardButton("📊 Статистика", callback_data="stats")
)
menu.add(
    KeyboardButton("📖 Инструкция")
)

# =====================================================
# SUB CHECK
# =====================================================

async def check_subscription(user_id):

    try:

        member = await bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )

        if member.status in [
            "member",
            "administrator",
            "creator"
        ]:
            return True

        return False

    except:
        return False

# =====================================================
# START
# =====================================================

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):

    sub = await check_subscription(
        message.from_user.id
    )

    if not sub:

        kb = InlineKeyboardMarkup()

        kb.add(
            InlineKeyboardButton(
                "📢 Подписаться",
                url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
            )
        )

        await message.answer(
            "❗ Для использования бота подпишись на канал",
            reply_markup=kb
        )

        return

    cursor.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?)",
        (
            message.from_user.id,
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
• Тексту песни

━━━━━━━━━━━━━━

📌 Просто отправь:
• голосовое
• кружок
• видео
• строчку из песни

И бот найдёт трек ❤️‍🔥
"""

    await message.answer(
        text,
        reply_markup=menu
    )

# =====================================================
# HELP
# =====================================================

@dp.message_handler(lambda m: m.text == "📖 Инструкция")
async def help_handler(message: types.Message):

    text = """
📖 КАК ПОЛЬЗОВАТЬСЯ

Бот умеет искать музыку по:

🎤 Голосовым
⭕ Кружкам
🎥 Видео
📝 Тексту песни

━━━━━━━━━━━━━━

📌 Примеры:

• отправь кружок
• отправь видео
• отправь голосовое
• отправь строчку песни

━━━━━━━━━━━━━━

После поиска бот отправит:

✅ Название трека
✅ Исполнителя
✅ Обложку
✅ Spotify
✅ YouTube
✅ Яндекс Музыка
✅ Genius

━━━━━━━━━━━━━━

🔥 Просто отправь сообщение
"""

    await message.answer(text)

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "⚙ Админ панель",
        reply_markup=admin_kb
    )

# =====================================================
# COVER
# =====================================================

def get_cover(artist, title):

    try:

        artist_l = artist.lower().strip()
        title_l = title.lower().strip()

        query = f"{artist} {title}"

        banned = [
            "remix",
            "live",
            "karaoke",
            "instrumental",
            "slowed",
            "speed up",
            "nightcore",
            "edit",
            "cover"
        ]

        # =====================================
        # 1. DEEZER (основной источник)
        # =====================================

        dz = requests.get(
            "https://api.deezer.com/search",
            params={"q": query},
            timeout=15
        ).json()

        data = dz.get("data", [])

        best = None
        best_score = -1

        for item in data:

            title_d = item.get("title", "").lower()
            artist_d = item.get("artist", {}).get("name", "").lower()

            album = item.get("album", {})
            cover = album.get("cover_xl")

            if not cover:
                continue

            # фильтр мусора
            if any(b in title_d for b in banned):
                continue

            score = 0

            if artist_l == artist_d:
                score += 100
            elif artist_l in artist_d:
                score += 60

            if title_l == title_d:
                score += 100
            elif title_l in title_d:
                score += 60

            # бонус за нормальный релиз
            if "feat" not in title_d:
                score += 5

            if score > best_score:
                best_score = score
                best = cover

        if best:
            return best

        # =====================================
        # 2. ITUNES (fallback)
        # =====================================

        r = requests.get(
            "https://itunes.apple.com/search",
            params={
                "term": query,
                "entity": "song",
                "limit": 10
            },
            timeout=15
        ).json()

        results = r.get("results", [])

        best = None
        best_score = -1

        for item in results:

            title_i = item.get("trackName", "").lower()
            artist_i = item.get("artistName", "").lower()

            if any(b in title_i for b in banned):
                continue

            score = 0

            if artist_l == artist_i:
                score += 100
            elif artist_l in artist_i:
                score += 50

            if title_l == title_i:
                score += 100
            elif title_l in title_i:
                score += 50

            if score > best_score:
                best_score = score
                best = item.get("artworkUrl100")

        if best:
            return best.replace("100x100", "600x600")

        return None

    except Exception as e:
        print("cover error:", e)
        return None

    try:

        query = f"{artist} {title}"

        r = requests.get(
            "https://itunes.apple.com/search",
            params={
                "term": query,
                "entity": "song",
                "limit": 15
            },
            timeout=15
        ).json()

        results = r.get("results")

        if not results:
            return None

        artist_lower = artist.lower()
        title_lower = title.lower()

        banned_words = [
            "remix",
            "live",
            "karaoke",
            "instrumental",
            "slowed",
            "speed up",
            "nightcore"
        ]

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

            bad = False

            for word in banned_words:

                if word in item_title:
                    bad = True
                    break

            if bad:
                continue

            score = 0

            if artist_lower == item_artist:
                score += 100

            elif artist_lower in item_artist:
                score += 50

            if title_lower == item_title:
                score += 100

            elif title_lower in item_title:
                score += 50

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

# =====================================================
# LINKS
# =====================================================

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

# =====================================================
# SEND RESULT
# =====================================================

async def send_result(
    message,
    artist,
    title,
    search_type
):

    # stats

    cursor.execute(
        "INSERT INTO searches (user_id, search_type, time) VALUES (?, ?, ?)",
        (
            message.from_user.id,
            search_type,
            str(datetime.now())
        )
    )

    conn.commit()

    # links

    links = get_links(
        artist,
        title
    )

    kb = InlineKeyboardMarkup(
        row_width=2
    )

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

    cover = get_cover(
        artist,
        title
    )

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

# =====================================================
# PROCESS AUDIO
# =====================================================

async def recognize_file(
    message,
    file_id,
    search_type
):

    wait = await message.answer(
        "🔎 Ищу трек..."
    )

    try:

        file = await bot.get_file(
            file_id
        )

        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{BOT_TOKEN}/{file.file_path}"
        )

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

        artist = result.get(
            "artist",
            "Unknown"
        )

        title = result.get(
            "title",
            "Unknown"
        )

        await wait.delete()

        await send_result(
            message,
            artist,
            title,
            search_type
        )

    except Exception as e:

        print(e)

        await wait.edit_text(
            "❌ Ошибка поиска"
        )

# =====================================================
# VOICE
# =====================================================

@dp.message_handler(content_types=["voice"])
async def voice_handler(message: types.Message):

    await recognize_file(
        message,
        message.voice.file_id,
        "voice"
    )

# =====================================================
# VIDEO NOTE
# =====================================================

@dp.message_handler(content_types=["video_note"])
async def circle_handler(message: types.Message):

    await recognize_file(
        message,
        message.video_note.file_id,
        "circle"
    )

# =====================================================
# VIDEO
# =====================================================

@dp.message_handler(content_types=["video"])
async def video_handler(message: types.Message):

    await recognize_file(
        message,
        message.video.file_id,
        "video"
    )

# =====================================================
# TEXT SEARCH
# =====================================================

@dp.message_handler(content_types=["text"])
async def text_handler(message: types.Message):

    if message.text.startswith("/admin"):
        return
    
    if message.text.startswith("/"):
        return

    if message.text == "📖 Инструкция":
        return

    wait = await message.answer("🔎 Ищу трек...")

    try:

        # =================================================
        # 1. ПОИСК ПО ТЕКСТУ ПЕСНИ
        # =================================================

        r = requests.get(
            "https://api.lyrics.ovh/suggest/" + message.text,
            timeout=15
        ).json()

        data = r.get("data")

        # =================================================
        # 2. ЕСЛИ lyrics.ovh НЕ НАШЕЛ -> fallback iTunes
        # =================================================

        if not data:

            r = requests.get(
                "https://itunes.apple.com/search",
                params={
                    "term": message.text,
                    "entity": "song",
                    "limit": 5
                },
                timeout=15
            ).json()

            results = r.get("results", [])

            if not results:
                await wait.edit_text("❌ Трек не найден")
                return

            best = results[0]

            artist = best.get("artistName", "Unknown")
            title = best.get("trackName", "Unknown")

        else:

            first = data[0]

            artist = first["artist"]["name"]
            title = first["title"]

        await wait.delete()

        await send_result(
            message,
            artist,
            title,
            "text"
        )

    except Exception as e:

        print("TEXT ERROR:", e)

        await wait.edit_text("❌ Ошибка поиска")
# =====================================================
# ADMIN PANEL
# =====================================================

@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_handler(call: types.CallbackQuery):

    await call.answer()

    await call.message.answer("КНОПКА РАБОТАЕТ")
    )
   
if __name__ == "__main__":
    
    executor.start_polling(
        dp,
        skip_updates=True
    )