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
ADMIN_ID = 1125040535
# =========================
# ЗАПУСК
# =========================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
# =========================
# БАЗА ДАННЫХ
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
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER UNIQUE
)
""")
conn.commit()
# =========================
# СОХРАНЕНИЕ ПОЛЬЗОВАТЕЛЕЙ
# =========================
def save_user(user_id):
    try:
        cursor.execute(
            "INSERT INTO users VALUES (?)",
            (user_id,)
        )
        conn.commit()
    except:
        pass
# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )
        return member.status in [
            "member",
            "administrator",
            "creator"
        ]
    except:
        return False
# =========================
# ГЛАВНОЕ МЕНЮ
# =========================
def main_menu():
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True
    )
    kb.add("🎵 Распознать")
    kb.add("📝 Поиск по тексту")
    kb.add("⭐ Избранное", "📜 История")
    kb.add("ℹ️ Помощь")
    return kb
# =========================
# КНОПКИ ТРЕКА
# =========================
def track_buttons(artist, title):
    q = f"{artist} {title}"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(
            "🎵 Яндекс Музыка",
            url=f"https://music.yandex.ru/search?text={q}"
        )
    )
    kb.add(
        InlineKeyboardButton(
            "🎧 Spotify",
            url=f"https://open.spotify.com/search/{q}"
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
# ОБЛОЖКА ТРЕКА
# =========================
def get_cover(artist, title):
    try:
        q = f"{artist} {title}"
        r = requests.get(
            "https://itunes.apple.com/search",
            params={
                "term": q,
                "media": "music",
                "limit": 1
            },
            timeout=10
        )
        data = r.json()
        if data["resultCount"] > 0:
            return data["results"][0][
                "artworkUrl100"
            ].replace("100x100", "600x600")
        return None
    except:
        return None
# =========================
# ПОИСК ПО ТЕКСТУ
# =========================
def lyrics_search(text):
    try:
        r = requests.get(
            "https://api.audd.io/findLyrics/",
            params={
                "q": text,
                "api_token": AUDD_API_KEY
            },
            timeout=20
        )
        data = r.json()
        if data.get("result"):
            first = data["result"][0]
            return (
                first["artist"],
                first["title"]
            )
        return None
    except:
        return None
# =========================
# /START
# =========================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    save_user(message.from_user.id)
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "📢 Подписаться",
                url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
            )
        )
        await message.answer(
            "❌ Для использования бота подпишитесь на канал",
            reply_markup=kb
        )
        return
    await message.answer(
        "🎵 <b>Music Finder Premium</b>\n\n"
        "Я умею находить музыку:\n\n"
        "🎤 По голосовым\n"
        "🎥 По видео\n"
        "⭕ По кружкам\n"
        "🎧 По аудио\n"
        "📝 По тексту песни\n"
        "🔗 По TikTok / Reels / Shorts ссылкам\n\n"
        "📌 Как пользоваться:\n\n"
        "1️⃣ Отправьте голосовое, видео, кружок или аудио\n"
        "2️⃣ Или отправьте строчку текста песни\n"
        "3️⃣ Бот найдёт музыку и отправит ссылки\n\n"
        "⭐ Вы можете сохранять треки в избранное",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
# =========================
# РАСПОЗНАТЬ
# =========================
@dp.message_handler(lambda m: m.text == "🎵 Распознать")
async def recognize_button(message: types.Message):
    await message.answer(
        "🎵 Отправьте:\n\n"
        "• голосовое\n"
        "• видео\n"
        "• кружок\n"
        "• аудио\n\n"
        "И я найду трек"
    )
# =========================
# ПОМОЩЬ
# =========================
@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help_button(message: types.Message):
    await message.answer(
        "ℹ️ <b>Помощь</b>\n\n"
        "🎤 Голосовые:\n"
        "отправьте голосовое сообщение\n\n"
        "🎥 Видео:\n"
        "отправьте видео с музыкой\n\n"
        "📝 Поиск по тексту:\n"
        "отправьте строчку песни\n\n"
        "🔗 TikTok / Reels / Shorts:\n"
        "отправьте ссылку",
        parse_mode="HTML"
    )
# =========================
# ИСТОРИЯ
# =========================
@dp.message_handler(lambda m: m.text == "📜 История")
async def history(message: types.Message):
    cursor.execute(
        "SELECT song FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10",
        (message.from_user.id,)
    )
    rows = cursor.fetchall()
    if not rows:
        await message.answer(
            "📜 История пока пустая"
        )
        return
    text = "📜 <b>Последние треки:</b>\n\n"
    for row in rows:
        text += f"• {row[0]}\n"
    await message.answer(
        text,
        parse_mode="HTML"
    )
# =========================
# ИЗБРАННОЕ
# =========================
@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def favorites(message: types.Message):
    cursor.execute(
        "SELECT song FROM favorites WHERE user_id=?",
        (message.from_user.id,)
    )
    rows = cursor.fetchall()
    if not rows:
        await message.answer(
            "⭐ Избранное пустое"
        )
        return
    await message.answer(
        "⭐ Ваши сохранённые треки:"
    )
    for row in rows:
        song = row[0]
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "🗑 Удалить",
                callback_data=f"delete|{song}"
            )
        )
        await message.answer(
            song,
            reply_markup=kb
        )
# =========================
# ДОБАВИТЬ В ИЗБРАННОЕ
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
        await callback.answer(
            "⚠️ Уже в избранном"
        )
        return
    cursor.execute(
        "INSERT INTO favorites VALUES (?, ?)",
        (user_id, song)
    )
    conn.commit()
    await callback.answer(
        "⭐ Добавлено в избранное"
    )
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
# =========================
# СТАТИСТИКА
# =========================
@dp.message_handler(commands=['stats'])
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )
    users = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM history"
    )
    searches = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM favorites"
    )
    favs = cursor.fetchone()[0]
    await message.answer(
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 Пользователей: {users}\n"
        f"🎵 Поисков: {searches}\n"
        f"⭐ Избранных: {favs}",
        parse_mode="HTML"
    )
# =========================
# РАСПОЗНАВАНИЕ
# =========================
@dp.message_handler(
    content_types=[
        'voice',
        'audio',
        'video_note',
        'video'
    ]
)
async def recognize_music(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer(
            "❌ Подпишитесь на канал"
        )
        return
    wait = await message.answer(
        "🔍 Ищу музыку..."
    )
    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        elif message.video_note:
            file_id = message.video_note.file_id
        else:
            file_id = message.video.file_id
        file = await bot.get_file(file_id)
        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{BOT_TOKEN}/{file.file_path}"
        )
        r = requests.post(
            "https://api.audd.io/",
            data={
                "api_token": AUDD_API_KEY,
                "url": file_url
            },
            timeout=30
        )
        data = r.json()
        if data.get("result"):
            artist = data["result"]["artist"]
            title = data["result"]["title"]
            song = f"{artist} — {title}"
            cursor.execute(
                "INSERT INTO history VALUES (?, ?)",
                (message.from_user.id, song)
            )
            conn.commit()
            image = get_cover(
                artist,
                title
            )
            kb = track_buttons(
                artist,
                title
            )
            await wait.delete()
            if image:
                await bot.send_photo(
                    message.chat.id,
                    photo=image,
                    caption=f"🎵 {song}",
                    reply_markup=kb
                )
            else:
                await message.answer(
                    f"🎵 {song}",
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
# ПОИСК ПО ССЫЛКАМ
# =========================
@dp.message_handler(content_types=['text'])
async def text_search(message: types.Message):
    text = message.text
    buttons = [
        "🎵 Распознать",
        "📝 Поиск по тексту",
        "⭐ Избранное",
        "📜 История",
        "ℹ️ Помощь"
    ]
    if text in buttons:
        return
    if (
        "tiktok.com" in text.lower()
        or "instagram.com" in text.lower()
        or "youtube.com/shorts" in text.lower()
    ):
        await message.answer(
            "🔗 Поиск по ссылкам пока работает в beta режиме\n\n"
            "📌 Для лучшего результата отправьте видео"
        )
        return
    wait = await message.answer(
        "🔎 Ищу песню по тексту..."
    )
    result = lyrics_search(text)
    if not result:
        await wait.edit_text(
            "❌ Ничего не найдено"
        )
        return
    artist, title = result
    song = f"{artist} — {title}"
    cursor.execute(
        "INSERT INTO history VALUES (?, ?)",
        (message.from_user.id, song)
    )
    conn.commit()
    image = get_cover(
        artist,
        title
    )
    kb = track_buttons(
        artist,
        title
    )
    await wait.delete()
    if image:
        await bot.send_photo(
            message.chat.id,
            photo=image,
            caption=f"🎵 Найдено:\n{song}",
            reply_markup=kb
        )
    else:
        await message.answer(
            f"🎵 Найдено:\n{song}",
            reply_markup=kb
        )
# =========================
# ЗАПУСК БОТА
# =========================
if __name__ == "__main__":
    executor.start_polli