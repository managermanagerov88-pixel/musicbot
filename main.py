import logging
import sqlite3
import requests
import os
import subprocess

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =====================
# CONFIG
# =====================

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
ADMIN_ID = 1125040535
CHANNEL = "@sp_rap"

# =====================
# INIT
# =====================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =====================
# DB
# =====================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, song TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS favs (user_id INTEGER, song TEXT)")
conn.commit()

# =====================
# MENU UI
# =====================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🎧 Распознать", "🔎 Поиск текста")
menu.row("📎 Поиск по ссылке", "⭐ Избранное")
menu.row("📜 История", "ℹ️ Помощь")

# =====================
# HELPERS
# =====================

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    conn.commit()

def stats():
    cur.execute("SELECT COUNT(*) FROM users")
    u = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM history")
    h = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM favs")
    f = cur.fetchone()[0]

    return u, h, f

# =====================
# COVER
# =====================

def cover(artist, title):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "limit": 1},
            timeout=10
        ).json()

        if r["resultCount"] > 0:
            return r["results"][0]["artworkUrl100"].replace("100x100", "600x600")
    except:
        pass
    return None

# =====================
# AUDD (file/url)
# =====================

def recognize_url(url):
    try:
        r = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "url": url},
            timeout=30
        )
        return r.json()
    except:
        return None

# =====================
# DOWNLOAD VIDEO (IMPORTANT)
# =====================

def download_audio(url):
    out = "audio.mp3"

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "-o", out,
        url
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(out):
        return out
    return None

# =====================
# START
# =====================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    add_user(m.from_user.id)
    await m.answer(
        "🎵 Music Finder Pro\n\nВыбери действие:",
        reply_markup=menu
    )

# =====================
# MEDIA (VOICE / VIDEO)
# =====================

@dp.message_handler(content_types=["voice", "audio", "video", "video_note"])
async def media(m: types.Message):

    msg = await m.answer("🎧 ищу...")

    file_id = (
        m.voice.file_id if m.voice else
        m.audio.file_id if m.audio else
        m.video.file_id if m.video else
        m.video_note.file_id
    )

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = recognize_url(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    artist = res["result"]["artist"]
    title = res["result"]["title"]

    song = f"{artist} - {title}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(artist, title)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}"))

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =====================
# TEXT SEARCH
# =====================

@dp.message_handler()
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    if m.text in ["🎧 Распознать","🔎 Поиск текста","📎 Поиск по ссылке","⭐ Избранное","📜 История","ℹ️ Помощь"]:
        return

    msg = await m.answer("🔎 ищу...")

    r = requests.get(
        "https://api.audd.io/findLyrics/",
        params={"q": m.text, "api_token": AUDD_API_KEY},
        timeout=20
    ).json()

    if not r.get("result"):
        return await msg.edit_text("❌ не найдено")

    artist = r["result"][0]["artist"]
    title = r["result"][0]["title"]

    song = f"{artist} - {title}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(artist, title)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}"))

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =====================
# LINK SEARCH (REAL)
# =====================

@dp.message_handler(lambda m: m.text == "📎 Поиск по ссылке")
async def link_help(m: types.Message):
    await m.answer(
        "📎 Отправь ссылку:\n"
        "TikTok / Reels / Shorts\n\n"
        "Я извлеку звук и найду трек 🎧"
    )

@dp.message_handler(lambda m: "tiktok" in (m.text or "") or "youtu" in (m.text or "") or "instagram" in (m.text or ""))
async def link_handler(m: types.Message):

    msg = await m.answer("📥 скачиваю видео...")

    audio = download_audio(m.text)

    if not audio:
        return await msg.edit_text("❌ не удалось скачать")

    res = recognize_url(audio)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    artist = res["result"]["artist"]
    title = res["result"]["title"]

    song = f"{artist} - {title}"

    img = cover(artist, title)

    if img:
        await bot.send_photo(m.chat.id, img, caption=song)
    else:
        await msg.edit_text(song)

# =====================
# CALLBACKS
# =====================

@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def fav(c: types.CallbackQuery):

    song = c.data.split("|")[1]

    cur.execute("INSERT INTO favs VALUES (?,?)", (c.from_user.id, song))
    conn.commit()

    await c.answer("⭐ добавлено")

# =====================
# ADMIN
# =====================

@dp.message_handler(commands=["admin"])
async def admin(m: types.Message):

    if m.from_user.id != ADMIN_ID:
        return

    u, h, f = stats()

    await m.answer(
        f"📊 ADMIN\n\n👥 {u}\n🔎 {h}\n⭐ {f}"
    )

# =====================
# RUN
# =====================

if __name__ == "__main__":
    executor.start_polling(dp)