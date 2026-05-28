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
# SUB CHECK (ВАЖНО)
# =========================

async def is_sub(user_id: int):
    try:
        chat = await bot.get_chat_member(CHANNEL, user_id)
        return chat.status in ["member", "administrator", "creator"]
    except:
        return False

async def guard(user_id, message):
    if not await is_sub(user_id):
        await message.answer("🚫 Подпишись на канал для доступа", reply_markup=sub_kb)
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

def cover(artist, title):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "limit": 1}
        ).json()

        if r.get("resultCount"):
            return r["results"][0]["artworkUrl100"].replace("100x100", "600x600")
    except:
        return None

def links(artist, title):
    q = f"{artist} {title}"
    return {
        "yt": f"https://www.youtube.com/results?search_query={q}",
        "sp": f"https://open.spotify.com/search/{q}",
        "ya": f"https://music.yandex.ru/search?text={q}",
        "genius": f"https://genius.com/search?q={q}"
    }

# =========================
# START
# =========================

@dp.message_handler(commands=["start"])
async def start(m: types.Message):

    if not await is_sub(m.from_user.id):
        return await m.answer("🚫 Доступ только после подписки", reply_markup=sub_kb)

    await m.answer("🎵 Music Finder\nВыбери действие:", reply_markup=menu)

# =========================
# CHECK SUB BUTTON
# =========================

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check(c: types.CallbackQuery):

    if await is_sub(c.from_user.id):
        await c.message.edit_text("✅ Доступ открыт")
        await bot.send_message(c.from_user.id, "🎵 Меню:", reply_markup=menu)
    else:
        await c.answer("❌ Ты не подписан", show_alert=True)

# =========================
# AUDIO / VOICE / VIDEO NOTE
# =========================

@dp.message_handler(content_types=["voice", "audio", "video_note"])
async def media(m: types.Message):

    if not await guard(m.from_user.id, m):
        return

    wait = await m.answer("🎧 ищу трек...")

    file_id = m.voice.file_id if m.voice else m.audio.file_id if m.audio else m.video_note.file_id

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    res = recognize(url)

    if not res or not res.get("result"):
        return await wait.edit_text("❌ не найдено")

    artist = res["result"]["artist"]
    title = res["result"]["title"]

    song = f"{artist} - {title}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(artist, title)
    l = links(artist, title)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶️ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("🎵 Yandex", url=l["ya"]),
        InlineKeyboardButton("📜 Genius", url=l["genius"])
    )
    kb.add(
        InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}")
    )

    text = f"🎵 {song}"

    if img:
        await bot.send_photo(m.chat.id, img, caption=text, reply_markup=kb)
    else:
        await wait.edit_text(text, reply_markup=kb)

# =========================
# TEXT SEARCH
# =========================

@dp.message_handler()
async def text(m: types.Message):

    if m.text.startswith("/"):
        return

    if not await guard(m.from_user.id, m):
        return

    wait = await m.answer("🔎 ищу...")

    r = requests.get(
        "https://api.audd.io/findLyrics/",
        params={"q": m.text, "api_token": AUDD_API_KEY},
        timeout=20
    ).json()

    if not r.get("result"):
        return await wait.edit_text("❌ не найдено")

    artist = r["result"][0]["artist"]
    title = r["result"][0]["title"]

    song = f"{artist} - {title}"

    cur.execute("INSERT INTO history VALUES (?,?)", (m.from_user.id, song))
    conn.commit()

    img = cover(artist, title)
    l = links(artist, title)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶️ YouTube", url=l["yt"]),
        InlineKeyboardButton("🎧 Spotify", url=l["sp"])
    )
    kb.add(
        InlineKeyboardButton("🎵 Yandex", url=l["ya"]),
        InlineKeyboardButton("📜 Genius", url=l["genius"])
    )
    kb.add(
        InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{song}")
    )

    text_out = f"🎵 {song}"

    if img:
        await bot.send_photo(m.chat.id, img, caption=text_out, reply_markup=kb)
    else:
        await wait.edit_text(text_out, reply_markup=kb)

# =========================
# FAVORITES ADD / REMOVE
# =========================

@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def fav(c: types.CallbackQuery):

    song = c.data.split("|", 1)[1]

    cur.execute("INSERT INTO favs VALUES (?,?)", (c.from_user.id, song))
    conn.commit()

    await c.answer("⭐ Добавлено")

# =========================
# FAVORITES LIST + REMOVE
# =========================

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def fav_list(m: types.Message):

    cur.execute("SELECT rowid, song FROM favs WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    if not rows:
        return await m.answer("⭐ пусто")

    text = "⭐ Избранное:\n\n"
    kb = InlineKeyboardMarkup()

    for r in rows[-10:]:
        text += f"• {r[1]}\n"
        kb.add(InlineKeyboardButton(f"❌ удалить {r[1][:15]}", callback_data=f"del|{r[0]}"))

    await m.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("del|"))
async def delete_fav(c: types.CallbackQuery):

    fav_id = c.data.split("|")[1]

    cur.execute("DELETE FROM favs WHERE rowid=?", (fav_id,))
    conn.commit()

    await c.answer("🗑 удалено")
    await c.message.delete()

# =========================
# HISTORY
# =========================

@dp.message_handler(lambda m: m.text == "📜 История")
async def history(m: types.Message):

    cur.execute("SELECT song FROM history WHERE user_id=?", (m.from_user.id,))
    rows = cur.fetchall()

    await m.answer("\n".join([r[0] for r in rows[-10:]]) if rows else "пусто")

# =========================
# HELP
# =========================

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help(m: types.Message):
    await m.answer(
        "🎵 Бот:\n"
        "🎧 голос/аудио → трек\n"
        "📹 видео → трек\n"
        "🔎 текст → поиск\n"
        "⭐ избранное\n📜 история"
    )

# =========================
# RUN
# =========================

if __name__ == "__main__":
    executor.start_polling(dp)