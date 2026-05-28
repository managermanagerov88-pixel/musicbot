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
# STATE (ONLY ONE MODE)
# =====================

WAIT_SEARCH = {}

# =====================
# UI
# =====================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🔎 Поиск")
menu.row("⭐ Избранное", "ℹ️ Помощь")

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
        await m.answer("🚫 Подпишись на канал", reply_markup=sub_kb)
        return False
    return True

# =====================
# HELPERS
# =====================

def audd_recognize(url):
    try:
        r = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "url": url},
            timeout=25
        )
        return r.json()
    except:
        return None


def lyrics_search(text):
    try:
        r = requests.get(
            "https://api.audd.io/findLyrics/",
            params={"q": text, "api_token": AUDD_API_KEY},
            timeout=20
        )
        return r.json()
    except:
        return None


def cover_real(artist, title):
    """
    ВАЖНО: фикс неправильных обложек
    теперь берём только точное совпадение
    """
    try:
        q = f"{artist} {title}"

        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": q, "limit": 1}
        ).json()

        if r.get("resultCount") > 0:
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
# USER REGISTER
# =====================

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, str(date.today())))
    conn.commit()

# =====================
# START
# =====================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    add_user(m.from_user.id)

    if not await is_sub(m.from_user.id):
        return await m.answer("🚫 Подпишись на канал", reply_markup=sub_kb)

    await m.answer(
        "🎧 SPACE SEARCH\n\n"
        "🔎 Поиск музыки по:\n"
        "• голосу\n"
        "• видео\n"
        "• тексту\n\n"
        "Нажми 🔎 Поиск и отправь любой контент",
        reply_markup=menu
    )

# =====================
# SINGLE SEARCH BUTTON (FIXED FLOW)
# =====================

@dp.message_handler(lambda m: m.text == "🔎 Поиск")
async def search(m: types.Message):

    if not await guard(m):
        return

    WAIT_SEARCH[m.from_user.id] = True

    await m.answer(
        "🎯 Режим поиска включён\n\n"
        "📩 Отправь:\n"
        "• голосовое\n"
        "• видео\n"
        "• текст\n\n"
        "Я всё распознаю автоматически"
    )

# =====================
# HELP
# =====================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):

    if not await guard(m):
        return

    await m.answer(
        "ℹ️ Как пользоваться:\n\n"
        "1️⃣ нажми Поиск\n"
        "2️⃣ отправь голос / видео / текст\n"
        "3️⃣ получи трек\n\n"
        "⭐ избранное — сохранение треков"
    )

# =====================
# FAVORITES
# =====================

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def fav(m: types.Message):

    if not await guard(m):
        return

    cur.execute("SELECT song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    if not rows:
        return await m.answer("⭐ пусто")

    kb = InlineKeyboardMarkup()
    text = "⭐ Избранное:\n\n"

    for r in rows:
        text += f"• {r[0]}\n"
        kb.add(InlineKeyboardButton("❌ удалить", callback_data=f"del|{r[0]}"))

    await m.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("del|"))
async def del_fav(c: types.CallbackQuery):

    song = c.data.split("|", 1)[1]

    cur.execute("DELETE FROM favs WHERE user_id=? AND song=?", (c.from_user.id, song))
    conn.commit()

    await c.answer("удалено")
    await c.message.delete()

# =====================
# MEDIA SEARCH (VOICE / VIDEO FIXED)
# =====================

@dp.message_handler(content_types=["voice", "video", "audio"])
async def media(m: types.Message):

    if not WAIT_SEARCH.get(m.from_user.id):
        return

    if not await guard(m):
        return

    WAIT_SEARCH[m.from_user.id] = False

    msg = await m.answer("🔎 ищу...")

    file_id = (
        m.voice.file_id if m.voice else
        m.video.file_id if m.video else
        m.audio.file_id if m.audio else None
    )

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = audd_recognize(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = res["result"]["artist"]
    t = res["result"]["title"]

    song = f"{a} - {t}"

    cur.execute("INSERT INTO stats VALUES (?,?,?)",
                (m.from_user.id, "media", str(datetime.now())))
    conn.commit()

    img = cover_real(a, t)
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
    kb.add(
        InlineKeyboardButton("⭐ в избранное", callback_data=f"fav|{song}")
    )

    text = f"🎵 {song}"

    if img:
        await bot.send_photo(m.chat.id, img, caption=text, reply_markup=kb)
    else:
        await msg.edit_text(text, reply_markup=kb)

# =====================
# TEXT SEARCH FIXED
# =====================

@dp.message_handler()
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    if not WAIT_SEARCH.get(m.from_user.id):
        return

    if not await guard(m):
        return

    WAIT_SEARCH[m.from_user.id] = False

    msg = await m.answer("🔎 ищу...")

    r = lyrics_search(m.text)

    if not r or not r.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = r["result"][0]["artist"]
    t = r["result"][0]["title"]

    song = f"{a} - {t}"

    img = cover_real(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("⭐ в избранное", callback_data=f"fav|{song}")
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
# ADMIN (FIXED 100%)
# =====================

@dp.message_handler(commands=["admin"])
async def admin(m: types.Message):

    if m.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM stats")
    searches = cur.fetchone()[0]

    await m.answer(
        f"🛠 ADMIN\n\n"
        f"👤 users: {users}\n"
        f"🔎 searches: {searches}"
    )

# =====================
# RUN
# =====================

if __name__ == "__main__":
    executor.start_polling(dp)