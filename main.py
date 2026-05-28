import logging
import sqlite3
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

# =====================
# НАСТРОЙКИ
# =====================

BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL_USERNAME = "@sp_rap"
ADMIN_ID = 1125040535

# =====================
# БОТ
# =====================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =====================
# БАЗА
# =====================

conn = sqlite3.connect("music.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER UNIQUE)")
cur.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, song TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS favs (user_id INTEGER, song TEXT)")
conn.commit()

# =====================
# УТИЛИТЫ
# =====================

def add_user(uid):
    try:
        cur.execute("INSERT INTO users VALUES (?)", (uid,))
        conn.commit()
    except:
        pass


async def check_sub(uid):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False


def menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎵 Распознать")
    kb.add("⭐ Избранное", "📜 История")
    kb.add("ℹ️ Помощь")
    return kb


def buttons(song):
    kb = InlineKeyboardMarkup()

    kb.add(InlineKeyboardButton("🎧 Яндекс", url=f"https://music.yandex.ru/search?text={song}"))
    kb.add(InlineKeyboardButton("🎵 Spotify", url=f"https://open.spotify.com/search/{song}"))
    kb.add(InlineKeyboardButton("🍎 Apple", url=f"https://music.apple.com/search?term={song}"))

    kb.add(InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}"))

    return kb


def cover(artist, title):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "media": "music", "limit": 1},
            timeout=10
        )
        data = r.json()

        if data["resultCount"] > 0:
            return data["results"][0]["artworkUrl100"].replace("100x100", "600x600")
    except:
        pass

    return None


def recognize_audd(file_url):
    try:
        r = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_KEY, "url": file_url},
            timeout=30
        )
        return r.json()
    except:
        return None


# =====================
# START
# =====================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    add_user(m.from_user.id)

    if not await check_sub(m.from_user.id):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))

        await m.answer("❌ Подпишись на канал", reply_markup=kb)
        return

    await m.answer("🎵 Отправь голосовое / видео / кружок", reply_markup=menu())


# =====================
# МЕНЮ
# =====================

@dp.message_handler(lambda m: m.text == "🎵 Распознать")
async def info(m: types.Message):
    await m.answer("🎧 Отправь голосовое, кружок или видео с музыкой")


@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):
    await m.answer("📌 Просто отправь голосовое или текст песни")


# =====================
# ИСТОРИЯ
# =====================

@dp.message_handler(lambda m: m.text == "📜 История")
async def history(m: types.Message):

    cur.execute("SELECT song FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10", (m.from_user.id,))
    rows = cur.fetchall()

    if not rows:
        return await m.answer("Пусто")

    txt = "📜 История:\n\n"
    for r in rows:
        txt += f"• {r[0]}\n"

    await m.answer(txt)


# =====================
# ИЗБРАННОЕ
# =====================

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def favs(m: types.Message):

    cur.execute("SELECT song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    if not rows:
        return await m.answer("Пусто")

    for r in rows:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🗑 удалить", callback_data=f"del|{r[0]}"))
        await m.answer(r[0], reply_markup=kb)


# =====================
# CALLBACKS
# =====================

@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def add_fav(c: types.CallbackQuery):
    song = c.data.split("|")[1]

    cur.execute("INSERT INTO favs VALUES (?,?)", (c.from_user.id, song))
    conn.commit()

    await c.answer("Добавлено ⭐")


@dp.callback_query_handler(lambda c: c.data.startswith("del|"))
async def del_fav(c: types.CallbackQuery):
    song = c.data.split("|")[1]

    cur.execute("DELETE FROM favs WHERE user_id=? AND song=?", (c.from_user.id, song))
    conn.commit()

    await c.message.delete()


# =====================
# ГЛАВНОЕ РАСПОЗНАВАНИЕ
# =====================

@dp.message_handler(content_types=["voice", "audio", "video_note", "video"])
async def audio(m: types.Message):

    await m.answer("🎧 ищу...")

    file_id = None

    if m.voice:
        file_id = m.voice.file_id
    elif m.audio:
        file_id = m.audio.file_id
    elif m.video_note:
        file_id = m.video_note.file_id
    elif m.video:
        file_id = m.video.file_id

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = recognize_audd(url)

    if not res or not res.get("result"):
        return await m.answer("не найдено ❌")

    artist = res["result"]["artist"]
    title = res["result"]["title"]
    song = f"{artist} - {title}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(artist, title)

    kb = buttons(song)

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await m.answer(song, reply_markup=kb)


# =====================
# TEXT SEARCH
# =====================

@dp.message_handler(content_types=["text"])
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    if len(m.text) < 3:
        return

    await m.answer("🔎 ищу по тексту...")

    r = requests.get(
        "https://api.audd.io/findLyrics/",
        params={"q": m.text, "api_token": AUDD_API_KEY},
        timeout=20
    ).json()

    if not r.get("result"):
        return await m.answer("не найдено ❌")

    artist = r["result"][0]["artist"]
    title = r["result"][0]["title"]

    song = f"{artist} - {title}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(artist, title)

    kb = buttons(song)

    if img:
        await bot.send_photo(m.chat.id, img, caption=song, reply_markup=kb)
    else:
        await m.answer(song, reply_markup=kb)


# =====================
# RUN
# =====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)