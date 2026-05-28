import logging
import sqlite3
import requests
from datetime import datetime, date

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
# DB
# =====================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
first_seen TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS favs (
user_id INTEGER,
song TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS stats (
user_id INTEGER,
type TEXT,
time TEXT
)""")

conn.commit()

# =====================
# STATE (ONLY ONE)
# =====================

search_mode = set()

# =====================
# UI
# =====================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🔎 Поиск")
menu.row("⭐ Избранное", "ℹ️ Помощь")

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
        await m.answer("🚫 Подпишись на канал")
        return False
    return True

# =====================
# HELPERS
# =====================

def audd(file_url):
    try:
        r = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "url": file_url},
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

            # FIX: убираем рандомные обложки
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

    if not await is_sub(m.from_user.id):
        return await m.answer("🚫 Подпишись")

    await m.answer(
        "🎧 SPACE SEARCH\n\n"
        "🔎 нажми Поиск → отправь голос/видео/текст",
        reply_markup=menu
    )

# =====================
# SEARCH MODE (FIXED)
# =====================

@dp.message_handler(lambda m: m.text == "🔎 Поиск")
async def search(m: types.Message):

    if not await guard(m):
        return

    search_mode.add(m.from_user.id)

    await m.answer("📩 отправь голос / видео / текст")

# =====================
# HELP
# =====================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):

    await m.answer(
        "ℹ️ как пользоваться:\n"
        "1. Поиск\n"
        "2. отправь контент\n"
        "3. получи трек"
    )

# =====================
# FAVORITES
# =====================

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def favs(m: types.Message):

    cur.execute("SELECT song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    if not rows:
        return await m.answer("⭐ пусто")

    kb = InlineKeyboardMarkup()
    text = "⭐ избранное:\n\n"

    for r in rows:
        text += f"• {r[0]}\n"
        kb.add(InlineKeyboardButton("❌ удалить", callback_data=f"del|{r[0]}"))

    await m.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("del|"))
async def delete(c: types.CallbackQuery):

    song = c.data.split("|", 1)[1]

    cur.execute("DELETE FROM favs WHERE user_id=? AND song=?", (c.from_user.id, song))
    conn.commit()

    await c.answer("удалено")
    await c.message.delete()

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

    img = cover(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("YouTube", url=l["yt"]),
        InlineKeyboardButton("Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("⭐", callback_data=f"fav|{song}")
    )

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =====================
# TEXT SEARCH (ONLY WHEN MODE ON)
# =====================

@dp.message_handler()
async def text(m: types.Message):

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
        InlineKeyboardButton("YouTube", url=l["yt"]),
        InlineKeyboardButton("Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("⭐", callback_data=f"fav|{song}")
    )

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =====================
# FAVORITE ADD
# =====================

@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def fav_add(c: types.CallbackQuery):

    song = c.data.split("|", 1)[1]

    cur.execute("INSERT INTO favs VALUES (?,?)", (c.from_user.id, song))
    conn.commit()

    await c.answer("добавлено")

# =====================
# ADMIN FIXED
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
        f"ADMIN\n\nusers: {users}\nstats: {stats}"
    )

# =====================
# RUN
# =====================

if __name__ == "__main__":
    executor.start_polling(dp)