import logging
import sqlite3
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

# ======================
# CONFIG
# ======================

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
ADMIN_ID = 1125040535
CHANNEL = "@sp_rap"

# ======================
# INIT
# ======================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ======================
# DB
# ======================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, song TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS favs (user_id INTEGER, song TEXT)")
conn.commit()

# ======================
# STATE
# ======================

state = {}

# ======================
# DB HELP
# ======================

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    conn.commit()

# ======================
# STATS
# ======================

def stats():
    cur.execute("SELECT COUNT(*) FROM users")
    u = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM history")
    h = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM favs")
    f = cur.fetchone()[0]

    return u, h, f

# ======================
# SUB CHECK
# ======================

async def check_sub(uid):
    try:
        m = await bot.get_chat_member(CHANNEL, uid)
        return m.status in ["member", "creator", "administrator"]
    except:
        return True  # чтобы не ломался бот

# ======================
# MENU
# ======================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🎵 Распознать", "⭐ Избранное")
menu.row("📜 История", "🔎 Поиск ссылки")
menu.row("ℹ️ Помощь")

# ======================
# TRACK BUTTONS
# ======================

def track_buttons(song):
    kb = InlineKeyboardMarkup()

    kb.row(
        InlineKeyboardButton("🎧 Яндекс", url=f"https://music.yandex.ru/search?text={song}"),
        InlineKeyboardButton("🎵 Spotify", url=f"https://open.spotify.com/search/{song}")
    )

    kb.row(
        InlineKeyboardButton("🍎 Apple", url=f"https://music.apple.com/search?term={song}"),
        InlineKeyboardButton("📖 Genius", url=f"https://genius.com/search?q={song}")
    )

    kb.add(InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}"))

    return kb

# ======================
# COVER
# ======================

def cover(artist, title):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "limit": 1},
            timeout=10
        ).json()

        if r["resultCount"]:
            return r["results"][0]["artworkUrl100"].replace("100x100", "600x600")
    except:
        pass
    return None

# ======================
# AUDD
# ======================

def recognize(url):
    try:
        r = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "url": url},
            timeout=25
        )
        return r.json()
    except:
        return None

# ======================
# START
# ======================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    add_user(m.from_user.id)

    await m.answer(
        "🎵 Music Bot\n\n"
        "📌 Выбери действие:",
        reply_markup=menu
    )

# ======================
# HELP
# ======================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):
    await m.answer("Отправь голос / видео / кружок или текст песни")

# ======================
# HISTORY
# ======================

@dp.message_handler(lambda m: m.text == "📜 История")
async def history(m: types.Message):

    cur.execute("SELECT song FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10", (m.from_user.id,))
    rows = cur.fetchall()

    await m.answer("\n".join([r[0] for r in rows]) if rows else "Пусто")

# ======================
# FAVORITES
# ======================

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def favs(m: types.Message):

    cur.execute("SELECT song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    if not rows:
        return await m.answer("Пусто")

    for r in rows[:10]:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🗑 удалить", callback_data=f"del|{r[0]}"))
        await m.answer(r[0], reply_markup=kb)

# ======================
# MEDIA
# ======================

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

    res = recognize(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    artist = res["result"]["artist"]
    title = res["result"]["title"]
    song = f"{artist} - {title}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(artist, title)
    kb = track_buttons(song)

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# ======================
# TEXT SEARCH
# ======================

@dp.message_handler(content_types=["text"])
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    if m.text in ["🎵 Распознать", "⭐ Избранное", "📜 История", "ℹ️ Помощь", "🔎 Поиск ссылки"]:
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
    kb = track_buttons(song)

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# ======================
# CALLBACKS (FIX SPAM!)
# ======================

@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def fav(c: types.CallbackQuery):

    song = c.data.split("|")[1]

    cur.execute("INSERT INTO favs VALUES (?,?)", (c.from_user.id, song))
    conn.commit()

    await c.answer("⭐ добавлено", show_alert=False)

@dp.callback_query_handler(lambda c: c.data.startswith("del|"))
async def delete(c: types.CallbackQuery):

    song = c.data.split("|")[1]

    cur.execute("DELETE FROM favs WHERE user_id=? AND song=?", (c.from_user.id, song))
    conn.commit()

    await c.message.delete()

# ======================
# LINK SEARCH (NEW)
# ======================

@dp.message_handler(lambda m: m.text == "🔎 Поиск ссылки")
async def link_help(m: types.Message):

    await m.answer(
        "🔎 Отправь ссылку:\n\n"
        "• TikTok\n"
        "• YouTube Shorts\n"
        "• Instagram Reels\n\n"
        "Я попробую найти трек 🎵"
    )

# ======================
# ADMIN FIXED
# ======================

@dp.message_handler(commands=["admin"])
async def admin(m: types.Message):

    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔ нет доступа")

    u, h, f = stats()

    await m.answer(
        f"📊 ADMIN PANEL\n\n"
        f"👥 users: {u}\n"
        f"🔎 searches: {h}\n"
        f"⭐ favs: {f}"
    )

# ======================
# RUN
# ======================

if __name__ == "__main__":
    executor.start_polling(dp)