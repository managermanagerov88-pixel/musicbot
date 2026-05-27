import logging
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

# ======================
# НАСТРОЙКИ
# ======================
BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL_USERNAME = "@sp_rap"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ======================
# ДАННЫЕ
# ======================
favorites = {}
history = {}

# ======================
# ПРОВЕРКА ПОДПИСКИ
# ======================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ======================
# ГЛАВНОЕ МЕНЮ
# ======================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("🎵 Распознать музыку")
    kb.add("⭐ Избранное", "📜 История")
    kb.add("📊 Статистика", "ℹ️ Помощь")

    return kb

# ======================
# START
# ======================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(
            f"❌ Подпишитесь на {CHANNEL_USERNAME}\n"
            "и нажмите /start снова."
        )
        return

    await message.answer(
        "🎧 <b>Добро пожаловать в Music Premium Bot</b>\n\n"
        "Я распознаю музыку по:\n"
        "🎤 голосу\n🔵 кружкам\n🎧 аудио\n\n"
        "Выберите действие ниже 👇",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# ======================
# МЕНЮ ОБРАБОТКА
# ======================
@dp.message_handler(lambda m: m.text == "🎵 Распознать музыку")
async def ask_audio(message: types.Message):
    await message.answer("🎧 Отправь голосовое, кружок или аудио")

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def show_fav(message: types.Message):
    user_id = message.from_user.id
    fav = favorites.get(user_id, [])

    if not fav:
        await message.answer("⭐ Избранное пустое")
        return

    await message.answer("⭐ <b>Твои любимые треки:</b>\n\n" + "\n".join(fav), parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "📜 История")
async def show_history(message: types.Message):
    user_id = message.from_user.id
    hist = history.get(user_id, [])

    if not hist:
        await message.answer("📜 История пуста")
        return

    await message.answer("📜 <b>Последние запросы:</b>\n\n" + "\n".join(hist[-10:]), parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "📊 Статистика")
async def stats(message: types.Message):
    user_id = message.from_user.id

    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"⭐ Избранное: {len(favorites.get(user_id, []))}\n"
        f"📜 История: {len(history.get(user_id, []))}",
        parse_mode="HTML"
    )

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "ℹ️ <b>Как пользоваться:</b>\n\n"
        "1. Нажми «🎵 Распознать музыку»\n"
        "2. Отправь голосовое или кружок\n"
        "3. Получи трек и ссылки\n\n"
        "⭐ Можно добавлять в избранное",
        parse_mode="HTML"
    )

# ======================
# КНОПКИ ССЫЛОК
# ======================
def make_buttons(artist, title):
    q = f"{artist} {title}"

    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton("🎧 Spotify", url=f"https://open.spotify.com/search/{q}"),
        InlineKeyboardButton("🎵 Яндекс Музыка", url=f"https://music.yandex.ru/search?text={q}"),
        InlineKeyboardButton("🍎 Apple Music", url=f"https://music.apple.com/search?term={q}"),
        InlineKeyboardButton("📖 Genius", url=f"https://genius.com/search?q={q}")
    )

    kb.add(
        InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{artist} - {title}")
    )

    return kb

# ======================
# ИЗБРАННОЕ
# ======================
@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def fav(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    song = callback.data.split("|")[1]

    favorites.setdefault(user_id, [])
    favorites[user_id].append(song)

    await callback.answer("Добавлено ⭐")

# ======================
# РАСПОЗНАВАНИЕ
# ======================
@dp.message_handler(content_types=['voice', 'audio', 'video_note'])
async def music(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(f"❌ Подпишись на {CHANNEL_USERNAME}")
        return

    await message.answer("🎧 Анализирую...")

    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        else:
            file_id = message.video_note.file_id

        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        data = {
            "api_token": AUDD_API_KEY,
            "url": file_url
        }

        r = requests.post("https://api.audd.io/", data=data, timeout=25)
        result = r.json()

        print(result)

        if result.get("result"):
            artist = result["result"]["artist"]
            title = result["result"]["title"]
            image = result["result"].get("album_image")

            history.setdefault(message.from_user.id, [])
            history[message.from_user.id].append(f"{artist} - {title}")

            text = f"🎵 <b>{artist} - {title}</b>"

            kb = make_buttons(artist, title)

            if image:
                await bot.send_photo(
                    message.chat.id,
                    photo=image,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=kb
                )
            else:
                await message.answer(text, parse_mode="HTML", reply_markup=kb)

        else:
            await message.answer("❌ Не удалось распознать трек")

    except Exception as e:
        print(e)
        await message.answer("❌ Ошибка обработки файла")

# ======================
# RUN
# ======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)