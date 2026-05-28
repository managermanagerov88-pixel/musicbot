import logging
import sqlite3
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL = "@sp_rap"
ADMIN_ID = 1125040535

# =========================
# INIT
# =========================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =========================
# DB
# =========================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, song TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS favs (user_id INTEGER, song TEXT)")
conn.commit()

# =========================
# USER STATES (ВАЖНО FIX)
# =========================

user_state = {}  # text_search mode

# =========================
# UI
# =========================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🎧 Распознать", "🔎 Поиск текста")
menu.row("📜 История", "⭐ Избранное")
menu.row("ℹ️ Помощь")

sub_kb = InlineKeyboardMarkup()
sub_kb.add(InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL.replace('@','')}"))
sub_kb.add(InlineKeyboardButton("🔄 Проверить", callback_data="check_sub"))

# =========================
# SUB CHECK (FIXED)
# =========================

async def is_sub(user_id: int):
    try:
        chat = await bot.get_chat_member(CHANNEL, user_id)
        return chat.status in ["member", "administrator", "creator"]
    except:
        return False

async def guard(user_id, message):
    if not await is_sub(user_id):
        await message.answer("🚫 Доступ только после подписки", reply_markup=sub_kb)
        return False
    return True

# =========================
# HELPERS
# =========================

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

# =========================
# START
# =========================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    if not await is_sub(m.from_user.id):
        return await m.answer("🚫 Подпишись", reply_markup=sub_kb)

    await m.answer("🎵 Music Bot готов", reply_markup=menu)

# =========================
# CHECK SUB
# =========================

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check(c: types.CallbackQuery):

    if await is_sub(c.from_user.id):
        await c.message.edit_text("✅ доступ открыт")
        await bot.send_message(c.from_user.id, "🎵 меню", reply_markup=menu)
    else:
        await c.answer("❌ не подписан", show_alert=True)

# =========================
# BUTTONS (FIX — no confusion anymore)
# =========================

@dp.message_handler(lambda m: m.text == "🔎 Поиск текста")
async def enable_search(m: types.Message):

    if not await guard(m.from_user.id, m):
        return

    user_state[m.from_user.id] = "text_search"
    await m.answer("✏️ Введите текст песни")

# =========================
# MEDIA
# =========================

@dp.message_handler(content_types=["voice", "audio", "video_note"])
async def media(m: types.Message):

    if not await guard(m.from_user.id, m):
        return

    msg = await m.answer("🎧 ищу...")

    file_id = m.voice.file_id if m.voice else m.audio.file_id if m.audio else m.video_note.file_id

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = recognize(url)

    if not res or not res.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = res["result"]["artist"]
    t = res["result"]["title"]

    song = f"{a} - {t}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶️ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("🎵 Yandex", url=l["ya"]),
        InlineKeyboardButton("📜 Genius", url=l["gn"])
    )

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =========================
# TEXT SEARCH (ONLY WHEN MODE ON)
# =========================

@dp.message_handler()
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    # ❗ FIX: ONLY SEARCH WHEN USER IS IN SEARCH MODE
    if user_state.get(m.from_user.id) != "text_search":
        return

    if not await guard(m.from_user.id, m):
        return

    user_state[m.from_user.id] = None  # reset mode

    msg = await m.answer("🔎 ищу...")

    r = requests.get(
        "https://api.audd.io/findLyrics/",
        params={"q": m.text, "api_token": AUDD_API_KEY},
        timeout=20
    ).json()

    if not r.get("result"):
        return await msg.edit_text("❌ не найдено")

    a = r["result"][0]["artist"]
    t = r["result"][0]["title"]

    song = f"{a} - {t}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(a, t)
    l = links(a, t)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶️ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =========================
# HISTORY
# =========================

@dp.message_handler(lambda m: m.text == "📜 История")
async def history(m: types.Message):

    cur.execute("SELECT song FROM history WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    await m.answer("\n".join([r[0] for r in rows[-10:]]) if rows else "пусто")

# =========================
# FAVORITES
# =========================

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def favs(m: types.Message):

    cur.execute("SELECT song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    await m.answer("\n".join([r[0] for r in rows[-10:]]) if rows else "пусто")

# =========================
# HELP
# =========================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):
    await m.answer(
        "🎵 Бот:\n"
        "🎧 голос → трек\n"
        "📹 видео → трек\n"
        "✏️ текст → поиск\n"
    )

# =========================
# RUN
# =========================

if __name__ == "__main__":
    executor.start_polling(dp)