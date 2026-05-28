import logging
import requests
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup
)

# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL_USERNAME = "@sp_rap"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("musicbot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER,
    song TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    user_id INTEGER,
    song TEXT
)
""")

conn.commit()

# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# =========================
# МЕНЮ
# =========================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("🎵 Распознать музыку")
    kb.add("⭐ Избранное", "📜 История")
    kb.add("ℹ️ Помощь")

    return kb

# =========================
# КНОПКИ ПОД ТРЕКОМ
# =========================
def make_links(artist, title):

    q = f"{artist} {title}"

    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            "🎧 Spotify",
            url=f"https://open.spotify.com/search/{q}"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🎵 Яндекс Музыка",
            url=f"https://music.yandex.ru/search?text={q}"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🍎 Apple Music",
            url=f"https://music.apple.com/search?term={q}"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "📖 Genius",
            url=f"https://genius.com/search?q={q}"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "⭐ Добавить в избранное",
            callback_data=f"fav|{artist} - {title}"
        )
    )

    return kb

# =========================
# ОБЛОЖКА
# =========================
def get_cover(artist, title):

    try:
        q = f"{artist} {title}"

        url = "https://itunes.apple.com/search"

        params = {
            "term": q,
            "media": "music",
            "limit": 1
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data["resultCount"] > 0:
            return data["results"][0]["artworkUrl100"].replace(
                "100x100",
                "600x600"
            )

        return None

    except:
        return None

# =========================
# START
# =========================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if not await check_sub(message.from_user.id):

        kb = InlineKeyboardMarkup()

        kb.add(
            InlineKeyboardButton(
                "📢 Подписаться",
                url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
            )
        )

        await message.answer(
            "❌ Для использования бота подпишитесь на канал\n\n"
            "После подписки нажмите /start",
            reply_markup=kb
        )

        return

    await message.answer(
        "🎵 <b>Добро пожаловать в Music Finder</b>\n\n"
        "Бот умеет:\n"
        "• распознавать музыку\n"
        "• искать треки\n"
        "• сохранять избранное\n"
        "• хранить историю\n\n"
        "📌 Как пользоваться:\n"
        "1️⃣ Нажмите «Распознать музыку»\n"
        "2️⃣ Отправьте голосовое, кружок или аудио\n"
        "3️⃣ Получите результат\n\n"
        "👇 Используйте меню ниже",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# =========================
# КНОПКИ МЕНЮ
# =========================
@dp.message_handler(lambda m: m.text == "🎵 Распознать музыку")
async def recognize(message: types.Message):

    await message.answer(
        "🎧 Отправьте:\n\n"
        "• голосовое\n"
        "• кружок\n"
        "• аудио\n\n"
        "И я найду трек"
    )

# =========================
# ПОМОЩЬ
# =========================
@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help_menu(message: types.Message):

    await message.answer(
        "ℹ️ <b>Помощь</b>\n\n"
        "🎵 Распознавание музыки:\n"
        "Отправьте голосовое, аудио или кружок\n\n"
        "⭐ Избранное:\n"
        "Сохраняйте любимые треки\n\n"
        "📜 История:\n"
        "Просматривайте последние найденные песни",
        parse_mode="HTML"
    )

# =========================
# ИСТОРИЯ
# =========================
@dp.message_handler(lambda m: m.text == "📜 История")
async def history_menu(message: types.Message):

    cursor.execute(
        "SELECT song FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10",
        (message.from_user.id,)
    )

    rows = cursor.fetchall()

    if not rows:
        await message.answer("📜 История пуста")
        return

    text = "📜 <b>Последние треки:</b>\n\n"

    for row in rows:
        text += f"• {row[0]}\n"

    await message.answer(text, parse_mode="HTML")

# =========================
# ИЗБРАННОЕ
# =========================
@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def favorites_menu(message: types.Message):

    cursor.execute(
        "SELECT song FROM favorites WHERE user_id=?",
        (message.from_user.id,)
    )

    rows = cursor.fetchall()

    if not rows:
        await message.answer("⭐ Избранное пустое")
        return

    await message.answer("⭐ Ваше избранное:")

    for row in rows:

        song = row[0]

        kb = InlineKeyboardMarkup()

        kb.add(
            InlineKeyboardButton(
                "🗑 Удалить",
                callback_data=f"delete|{song}"
            )
        )

        await message.answer(song, reply_markup=kb)

# =========================
# ДОБАВЛЕНИЕ В ИЗБРАННОЕ
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def add_favorite(callback: types.CallbackQuery):

    user_id = callback.from_user.id
    song = callback.data.split("|")[1]

    cursor.execute(
        "SELECT * FROM favorites WHERE user_id=? AND song=?",
        (user_id, song)
    )

    exist = cursor.fetchone()

    if exist:
        await callback.answer("⚠️ Уже в избранном")
        return

    cursor.execute(
        "INSERT INTO favorites VALUES (?, ?)",
        (user_id, song)
    )

    conn.commit()

    await callback.answer("⭐ Добавлено")

# =========================
# УДАЛЕНИЕ ИЗ ИЗБРАННОГО
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("delete|"))
async def delete_favorite(callback: types.CallbackQuery):

    user_id = callback.from_user.id
    song = callback.data.split("|")[1]

    cursor.execute(
        "DELETE FROM favorites WHERE user_id=? AND song=?",
        (user_id, song)
    )

    conn.commit()

    await callback.message.edit_text(
        f"❌ Удалено:\n{song}"
    )

    await callback.answer("Удалено")

# =========================
# РАСПОЗНАВАНИЕ МУЗЫКИ
# =========================
@dp.message_handler(content_types=['voice', 'audio', 'video_note'])
async def music(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(
            f"❌ Подпишитесь на {CHANNEL_USERNAME}"
        )
        return

    wait = await message.answer(
        "🎧 Распознаю музыку..."
    )

    try:

        if message.voice:
            file_id = message.voice.file_id

        elif message.audio:
            file_id = message.audio.file_id

        else:
            file_id = message.video_note.file_id

        file = await bot.get_file(file_id)

        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{BOT_TOKEN}/{file.file_path}"
        )

        data = {
            "api_token": AUDD_API_KEY,
            "url": file_url
        }

        r = requests.post(
            "https://api.audd.io/",
            data=data,
            timeout=30
        )

        result = r.json()

        if result.get("result"):

            artist = result["result"]["artist"]
            title = result["result"]["title"]

            text = f"🎵 {artist} — {title}"

            # история
            cursor.execute(
                "INSERT INTO history VALUES (?, ?)",
                (message.from_user.id, text)
            )

            conn.commit()

            # обложка
            image = get_cover(artist, title)

            kb = make_links(artist, title)

            await wait.delete()

            if image:

                await bot.send_photo(
                    message.chat.id,
                    photo=image,
                    caption=text,
                    reply_markup=kb
                )

            else:

                await message.answer(
                    text,
                    reply_markup=kb
                )

        else:

            await wait.edit_text(
                "❌ Трек не найден"
            )

    except Exception as e:

        print(e)

        await wait.edit_text(
            "❌ Ошибка обработки"
        )

# =========================
# RUN
# =========================
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    executor.start_polling(dp)