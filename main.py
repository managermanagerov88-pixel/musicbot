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
time TEXT
)
""")

conn.commit()

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


# =====================
# FIXED COVER (REAL FIX)
# =====================

def cover(artist, title):
    try:
        q = f"{artist} {title}".strip()

        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": q, "limit": 10}
        ).json()

        if r.get("resultCount", 0) == 0:
            return None

        best = None
        best_score = 0

        for item in r["results"]:
            a = item.get("artistName", "").lower()
            t = item.get("trackName", "").lower()

            score = 0

            if artist.lower() in a:
                score += 2
            if title.lower() in t:
                score += 2
            if "artworkUrl100" in item:
                score += 1

            if score > best_score:
                best_score = score
                best = item

        if best and "artworkUrl100" in best:
            return best["artworkUrl100"].replace("100x100", "600x600")

        return None

    except:
        return None


# =====================
# LINKS
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

    await m.answer("🎧 Bot ready")


# =====================
# PROCESS
# =====================

async def send_track(m, artist, title):

    # ⚡ FIXED STATS (admin will work now)
    cur.execute("INSERT INTO stats VALUES (?,?)",
                (m.from_user.id, str(datetime.now())))
    conn.commit()

    img = cover(artist, title)
    l = links(artist, title)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("🎵 Yandex", url=l["ya"]),
        InlineKeyboardButton("📜 Genius", url=l["gn"])
    )

    text = f"🎵 {artist} - {title}"

    if img:
        await bot.send_photo(m.chat.id, img, caption=text, reply_markup=kb)
    else:
        await m.answer(text, reply_markup=kb)


# =====================
# MEDIA HANDLER
# =====================

@dp.message_handler(content_types=["voice", "video", "audio", "video_note"])
async def media(m: types.Message):

    msg = await m.answer("🔎 ищу...")

    file_id = (
        m.voice.file_id if m.voice else
        m.video.file_id if m.video else
        m.audio.file_id if m.audio else
        m.video_note.file_id
    )

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = audd(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = res["result"].get("artist", "Unknown")
    t = res["result"].get("title", "Unknown")

    await send_track(m, a, t)


# =====================
# ADMIN (FIXED)
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