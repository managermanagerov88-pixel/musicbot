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

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
first_seen TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS history (
user_id INTEGER,
song TEXT,
type TEXT,
time TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS favs (
user_id INTEGER,
song TEXT
)
""")

conn.commit()

# =====================
# STATE
# =====================

state = {}
STATE_TEXT = "text"

# =====================
# UI
# =====================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🎧 Распознать", "🔎 Поиск текста")
menu.row("⭐ Избранное", "ℹ️ Помощь")

sub_kb = InlineKeyboardMarkup()
sub_kb.add(
    InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL.replace('@','')}"),
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
        await m.answer("🚫 Подпишись на канал", reply_markup=sub_kb)
        return False
    return True

# =====================
# HELPERS
# =====================

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


def cover(a, t):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{a} {t}", "limit": 1}
        ).json()

        if r.get("resultCount"):
            return r["results"][0]["artworkUrl100"].replace("100x100", "600x600")
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
# USERS
# =====================

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, str(date.today())))
    conn.commit()

# =====================
# START (ИСПРАВЛЕНО)
# =====================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    add_user(m.from_user.id)

    if not await is_sub(m.from_user.id):
        return await m.answer("🚫 Подпишись", reply_markup=sub_kb)

    await m.answer(
        "🎧 SPACE SEARCH - поиск музыки по:\n"
        "• Голосовым\n"
        "• Кружкам\n"
        "• Видео\n"
        "• Отрывкам текста\n\n"
        "Искать треки проще, чем ты думаешь! ❤️‍🔥",
        reply_markup=menu
    )

# =====================
# MENU ACTIONS
# =====================

@dp.message_handler(lambda m: m.text == "🎧 Распознать")
async def rec(m: types.Message):

    if not await guard(m):
        return

    await m.answer("🔎 Отправь гс/кружок или видео")

@dp.message_handler(lambda m: m.text == "🔎 Поиск текста")
async def text_mode(m: types.Message):

    if not await guard(m):
        return

    state[m.from_user.id] = STATE_TEXT
    await m.answer("✏️ Введите отрывок текста песни")

# =====================
# MEDIA SEARCH (VOICE / VIDEO / NOTE)
# =====================

@dp.message_handler(content_types=["voice", "audio", "video_note", "video"])
async def media(m: types.Message):

    if not await guard(m):
        return

    msg = await m.answer("🎧 ищу трек...")

    file_id = (
        m.voice.file_id if m.voice
        else m.audio.file_id if m.audio
        else m.video_note.file_id if m.video_note
        else None
    )

    if not file_id:
        return await msg.edit_text("❌ не поддерживается")

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = recognize(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = res["result"]["artist"]
    t = res["result"]["title"]

    song = f"{a} - {t}"

    cur.execute("INSERT INTO history VALUES (?,?,?,?)",
                (m.from_user.id, song, "media", str(datetime.now())))
    conn.commit()

    img = cover(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("▶ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"]),
        InlineKeyboardButton("🎵 Yandex", url=l["ya"]),
        InlineKeyboardButton("📜 Genius", url=l["gn"])
    )
    kb.add(
        InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}")
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

    if state.get(m.from_user.id) != STATE_TEXT:
        return

    if not await guard(m):
        return

    state[m.from_user.id] = None

    msg = await m.answer("🔎 ищу...")

    r = requests.get(
        "https://api.audd.io/findLyrics/",
        params={"q": m.text, "api_token": AUDD_API_KEY}
    ).json()

    if not r.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = r["result"][0]["artist"]
    t = r["result"][0]["title"]

    song = f"{a} - {t}"

    cur.execute("INSERT INTO history VALUES (?,?,?,?)",
                (m.from_user.id, song, "text", str(datetime.now())))
    conn.commit()

    img = cover(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}")
    )

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =====================
# FAVORITES (FIXED)
# =====================

@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def fav_add(c: types.CallbackQuery):

    song = c.data.split("|", 1)[1]

    cur.execute("INSERT INTO favs VALUES (?,?)", (c.from_user.id, song))
    conn.commit()

    await c.answer("⭐ добавлено")

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def fav_list(m: types.Message):

    cur.execute("SELECT song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    if not rows:
        return await m.answer("⭐ пусто")

    kb = InlineKeyboardMarkup()

    text = "⭐ Избранное:\n\n"

    for i, r in enumerate(rows[-10:]):
        text += f"• {r[0]}\n"
        kb.add(InlineKeyboardButton(f"❌ удалить {i+1}", callback_data=f"del|{r[0]}"))

    await m.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("del|"))
async def fav_del(c: types.CallbackQuery):

    song = c.data.split("|", 1)[1]

    cur.execute("DELETE FROM favs WHERE user_id=? AND song=?", (c.from_user.id, song))
    conn.commit()

    await c.answer("🗑 удалено")
    await c.message.delete()

# =====================
# HELP (FIXED)
# =====================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):

    await m.answer(
        "ℹ️ SPACE SEARCH\n\n"
        "🎧 голос / видео → трек\n"
        "✏️ текст → поиск песни\n"
        "⭐ избранное\n\n"
        "📌 Просто отправь медиа или текст"
    )

# =====================
# ADMIN PANEL (/admin FIXED)
# =====================

@dp.message_handler(commands=["admin"])
async def admin(m: types.Message):

    if m.from_user.id != ADMIN_ID:
        return

    today = str(date.today())

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE first_seen=?", (today,))
    today_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM history")
    total_search = cur.fetchone()[0]

    cur.execute("SELECT user_id, COUNT(*) FROM history GROUP BY user_id")
    per_user = cur.fetchall()

    text = (
        f"🛠 ADMIN PANEL\n\n"
        f"👤 Users total: {total_users}\n"
        f"📅 Today users: {today_users}\n"
        f"🔎 Total searches: {total_search}\n\n"
        f"👥 Activity:\n"
    )

    for u in per_user[:10]:
        text += f"• {u[0]} → {u[1]} запросов\n"

    await m.answer(text)

# =====================
# RUN
# =====================

if __name__ == "__main__":
    executor.start_polling(dp)