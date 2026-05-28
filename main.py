import logging
import sqlite3
import requests
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =====================
# CONFIG
# =====================

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL = "@sp_rap"
ADMIN_ID = 1125040535

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =====================
# DB (ONLY USERS + STATS)
# =====================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
first_seen TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS stats (
user_id INTEGER,
type TEXT,
time TEXT
)
""")

conn.commit()

# =====================
# STATE (SIMPLE AND STABLE)
# =====================

search_mode = set()

# =====================
# UI
# =====================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🔎 Поиск")
menu.row("ℹ️ Помощь")

sub_kb = InlineKeyboardMarkup()
sub_kb.add(
    InlineKeyboardButton("📢 Подписка", url=f"https://t.me/{CHANNEL.replace('@','')}"),
    InlineKeyboardButton("🔄 Проверить", callback_data="check_sub")
)

# =====================
# SUB CHECK
# =====================

async def is_sub(user_id):
    try:
        chat = await bot.get_chat_member(CHANNEL, user_id)
        return chat.status in ["member", "administrator", "creator"]
    except:
        return False

async def guard(m):
    if not await is_sub(m.from_user.id):
        await m.answer("🚫 подпишись на канал", reply_markup=sub_kb)
        return False
    return True

# =====================
# HELPERS
# =====================

def audd(url):
    try:
        r = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "url": url},
            timeout=25
        )
        return r.json()
    except:
        return None


def lyrics(text):
    try:
        r = requests.get(
            "https://api.audd.io/findLyrics/",
            params={"q": text, "api_token": AUDD_API_KEY},
            timeout=20
        )
        return r.json()
    except:
        return None


def cover(artist, title):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "limit": 1}
        ).json()

        if r.get("resultCount", 0) > 0:
            item = r["results"][0]

            if artist.lower() in item["artistName"].lower():
                return item["artworkUrl100"].replace("100x100", "600x600")

        return None
    except:
        return None


def links(a, t):
    q = f"{a} {t}"
    return {
        "yt": f"https://youtube.com/results?search_query={q}",
        "sp": f"https://open.spotify.com/search/{q}",
        "ya": f"https://music.yandex.ru/search?text={q}",
        "gn": f"https://genius.com/search?q={q}"
    }

# =====================
# START
# =====================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)",
                (m.from_user.id, str(datetime.now())))
    conn.commit()

    if not await is_sub(m.from_user.id):
        return await m.answer("🚫 подпишись на канал", reply_markup=sub_kb)

    await m.answer(
        "🎧 SPACE SEARCH\n\n"
        "🔎 нажми Поиск → отправь голос / видео / текст",
        reply_markup=menu
    )

# =====================
# SEARCH MODE
# =====================

@dp.message_handler(lambda m: m.text == "🔎 Поиск")
async def search(m: types.Message):

    if not await guard(m):
        return

    search_mode.add(m.from_user.id)

    await m.answer(
        "📩 режим поиска включён\n\n"
        "Отправь:\n"
        "• голосовое\n"
        "• видео\n"
        "• текст\n\n"
        "Я найду трек автоматически"
    )

# =====================
# HELP
# =====================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):

    await m.answer(
        "ℹ️ инструкция:\n\n"
        "1. нажми Поиск\n"
        "2. отправь контент\n"
        "3. получи трек + ссылки\n\n"
        "поддержка: голос / видео / текст"
    )

# =====================
# MEDIA SEARCH (VOICE / VIDEO / AUDIO)
# =====================

@dp.message_handler(content_types=["voice", "video", "audio"])
async def media(m: types.Message):

    if m.from_user.id not in search_mode:
        return

    search_mode.discard(m.from_user.id)

    msg = await m.answer("🔎 ищу...")

    file_id = (
        m.voice.file_id if m.voice else
        m.video.file_id if m.video else
        m.audio.file_id
    )

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = audd(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = res["result"]["artist"]
    t = res["result"]["title"]

    song = f"{a} - {t}"

    cur.execute("INSERT INTO stats VALUES (?,?,?)",
                (m.from_user.id, "media", str(datetime.now())))
    conn.commit()

    img = cover(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("🎵 Yandex", url=l["ya"]),
        InlineKeyboardButton("📜 Genius", url=l["gn"])
    )

    text = f"🎵 {song}"

    if img:
        await bot.send_photo(m.chat.id, img, caption=text, reply_markup=kb)
    else:
        await msg.edit_text(text, reply_markup=kb)

# =====================
# TEXT SEARCH
# =====================

@dp.message_handler()
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    if m.from_user.id not in search_mode:
        return

    search_mode.discard(m.from_user.id)

    msg = await m.answer("🔎 ищу...")

    r = lyrics(m.text)

    if not r or not r.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = r["result"][0]["artist"]
    t = r["result"][0]["title"]

    song = f"{a} - {t}"

    img = cover(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )

    text = f"🎵 {song}"

    if img:
        await bot.send_photo(m.chat.id, img, caption=text, reply_markup=kb)
    else:
        await msg.edit_text(text, reply_markup=kb)

# =====================
# ADMIN PANEL (STABLE)
# =====================

@dp.message_handler(commands=["admin"])
async def admin(m: types.Message):

    if m.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM stats")
    stats = cur.fetchone()[0]

    await m.answer(
        f"🛠 ADMIN PANEL\n\n"
        f"👤 users: {users}\n"
        f"🔎 searches: {stats}"
    )

# =====================
# RUN
# =====================

if __name__ == "__main__":
    executor.start_polling(dp)