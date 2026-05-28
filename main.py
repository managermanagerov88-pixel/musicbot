import logging
import sqlite3
import requests

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
# UI
# =====================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.row("🎧 Распознать", "🔎 Поиск текста")
menu.row("📹 Поиск по видео")
menu.row("⭐ Избранное", "📜 История")
menu.row("ℹ️ Помощь")

sub_kb = InlineKeyboardMarkup()
sub_kb.add(InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL.replace('@','')}"))
sub_kb.add(InlineKeyboardButton("🔄 Проверить", callback_data="check_sub"))

# =====================
# HELPERS
# =====================

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    conn.commit()

# ✅ ВАЖНО: ПРАВИЛЬНАЯ ПРОВЕРКА ПОДПИСКИ
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print("SUB CHECK ERROR:", e)
        return False

def recognize(url):
    try:
        r = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "url": url},
            timeout=30
        )
        return r.json()
    except:
        return None

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

def build_links(artist, title):
    q = f"{artist} {title}"
    return {
        "spotify": f"https://open.spotify.com/search/{q.replace(' ', '%20')}",
        "youtube": f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}",
        "yandex": f"https://music.yandex.ru/search?text={q.replace(' ', '%20')}"
    }

# =====================
# START
# =====================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    add_user(m.from_user.id)

    if not await is_subscribed(m.from_user.id):
        return await m.answer(
            "🚫 Доступ только после подписки на канал",
            reply_markup=sub_kb
        )

    await m.answer("🎵 Music Finder Pro\n\nВыбери действие:", reply_markup=menu)

# =====================
# CHECK SUB BUTTON
# =====================

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check(c: types.CallbackQuery):

    if await is_subscribed(c.from_user.id):
        await c.message.edit_text("✅ доступ открыт!")
        await bot.send_message(c.from_user.id, "🎵 Меню:", reply_markup=menu)
    else:
        await c.answer("❌ подписка не найдена", show_alert=True)

# =====================
# BLOCK IF NOT SUBBED (ВАЖНО)
# =====================

async def guard(user_id, message: types.Message):
    if not await is_subscribed(user_id):
        await message.answer("🚫 сначала подпишись", reply_markup=sub_kb)
        return False
    return True

# =====================
# MEDIA
# =====================

@dp.message_handler(content_types=["voice", "audio", "video_note"])
async def media(m: types.Message):

    if not await guard(m.from_user.id, m):
        return

    msg = await m.answer("🎧 анализ...")

    file_id = (
        m.voice.file_id if m.voice else
        m.audio.file_id if m.audio else
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
    links = build_links(artist, title)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🎧 Spotify", url=links["spotify"]),
        InlineKeyboardButton("▶️ YouTube", url=links["youtube"])
    )
    kb.add(
        InlineKeyboardButton("🎵 Яндекс", url=links["yandex"])
    )

    if img:
        await bot.send_photo(m.chat.id, img, caption=f"🎵 {song}", reply_markup=kb)
    else:
        await msg.edit_text(f"🎵 {song}", reply_markup=kb)

# =====================
# TEXT SEARCH
# =====================

@dp.message_handler()
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    if not await guard(m.from_user.id, m):
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
    links = build_links(artist, title)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🎧 Spotify", url=links["spotify"]),
        InlineKeyboardButton("▶️ YouTube", url=links["youtube"])
    )

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await msg.edit_text(song, reply_markup=kb)

# =====================
# VIDEO
# =====================

@dp.message_handler(content_types=["video"])
async def video(m: types.Message):

    if not await guard(m.from_user.id, m):
        return

    msg = await m.answer("📹 анализ...")

    file = await bot.get_file(m.video.file_id)
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

    if img:
        await bot.send_photo(m.chat.id, img, caption=song)
    else:
        await msg.edit_text(song)

# =====================
# BUTTONS
# =====================

@dp.message_handler(lambda m: m.text == "📜 История")
async def history(m: types.Message):

    cur.execute("SELECT song FROM history WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    await m.answer("\n".join([r[0] for r in rows[-10:]]) if rows else "пусто")

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def favs(m: types.Message):

    cur.execute("SELECT song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    await m.answer("\n".join([r[0] for r in rows[-10:]]) if rows else "пусто")

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):
    await m.answer(
        "🎵 Бот:\n"
        "🎧 аудио → трек\n"
        "📹 видео → трек\n"
        "🔎 текст → поиск\n"
        "⭐ избранное\n📜 история"
    )

# =====================
# ADMIN
# =====================

@dp.message_handler(commands=["admin"])
async def admin(m: types.Message):

    if m.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT COUNT(*) FROM users")
    u = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM history")
    h = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM favs")
    f = cur.fetchone()[0]

    await m.answer(f"📊 ADMIN\n\n👥 {u}\n🔎 {h}\n⭐ {f}")

# =====================
# RUN
# =====================

if __name__ == "__main__":
    executor.start_polling(dp)