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
CREATE TABLE IF NOT EXISTS stats (
user_id INTEGER,
type TEXT,
time TEXT
)
""")

conn.commit()

# =====================
# UI
# =====================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
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

# =====================
# AUDIO IDENTIFY
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

# =====================
# LYRICS (optional fallback)
# =====================

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

# =====================
# COVER (FIXED - STABLE)
# =====================

def cover(artist, title):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "limit": 10}
        ).json()

        if r.get("resultCount", 0) == 0:
            return None

        for item in r["results"]:
            if "artworkUrl100" in item:
                return item["artworkUrl100"].replace("100x100", "600x600")

        return None
    except:
        return None

# =====================
# LINKS (ALWAYS FULL)
# =====================

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

    await m.answer(
        "🎧 SPACE SEARCH\n\n"
        "📌 Отправь:\n"
        "• голос\n"
        "• кружок\n"
        "• видео\n"
        "• текст\n\n"
        "И я найду трек автоматически 🔎",
        reply_markup=menu
    )

# =====================
# HELP
# =====================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):

    await m.answer(
        "ℹ️ Как пользоваться:\n\n"
        "1. просто отправь голос / кружок / видео / текст\n"
        "2. бот сам распознаёт музыку\n"
        "3. получишь ссылки + обложку\n\n"
        "💡 можно отправлять подряд без кнопок"
    )

# =====================
# MAIN SEARCH (NO BUTTON MODE ANYMORE)
# =====================

@dp.message_handler(content_types=["voice", "video", "audio", "video_note", "text"])
async def handler(m: types.Message):

    # ignore commands
    if m.text and m.text.startswith("/"):
        return

    await process(m)

# =====================
# CORE PROCESS
# =====================

async def process(m: types.Message):

    msg = await m.answer("🔎 ищу трек...")

    file_id = None

    if m.voice:
        file_id = m.voice.file_id
    elif m.video:
        file_id = m.video.file_id
    elif m.audio:
        file_id = m.audio.file_id
    elif m.video_note:
        file_id = m.video_note.file_id
    elif m.text:
        # text search fallback
        res = lyrics(m.text)
        if not res or not res.get("result"):
            return await msg.edit_text("❌ не найдено")

        item = res["result"][0]
        a = item.get("artist", "Unknown")
        t = item.get("title", m.text)

        await send_result(m, msg, a, t)
        return

    # audio/video recognition
    if not file_id:
        return await msg.edit_text("❌ не найдено")

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = audd(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    item = res["result"]

    a = item.get("artist", "Unknown")
    t = item.get("title", "Unknown")

    await send_result(m, msg, a, t)

# =====================
# SEND RESULT
# =====================

async def send_result(m, msg, a, t):

    cur.execute("INSERT INTO stats VALUES (?,?,?)",
                (m.from_user.id, "search", str(datetime.now())))
    conn.commit()

    song = f"{a} - {t}"

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
# ADMIN PANEL
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
        f"🛠 ADMIN PANEL\n\n"
        f"👤 users: {users}\n"
        f"🔎 searches: {searches}"
    )

# =====================
# RUN
# =====================

if __name__ == "__main__":
    executor.start_polling(dp)