import logging
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

# ======================
# НАСТРОЙКИ
# ======================
BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL_USERNAME = "@sp_rap"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

favorites = {}
history = {}

# ======================
# ПОДПИСКА
# ======================
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ======================
# ГЛАВНОЕ МЕНЮ (КРАСИВОЕ)
# ======================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("🎵 Распознать музыку")
    kb.add("⭐ Избранное", "📜 История")
    kb.add("ℹ️ Помощь")

    return kb

# ======================
# КНОПКИ ССЫЛОК
# ======================
def make_links(artist, title):
    q = f"{artist} {title}"

    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton("🎧 Spotify", url=f"https://open.spotify.com/search/{q}"),
        InlineKeyboardButton("🎵 Яндекс Музыка", url=f"https://music.yandex.ru/search?text={q}"),
        InlineKeyboardButton("🍎 Apple Music", url=f"https://music.apple.com/search?term={q}"),
        InlineKeyboardButton("📖 Genius", url=f"https://genius.com/search?q={q}")
    )

    return kb

# ======================
# ОБЛОЖКА (iTunes — стабильно)
# ======================
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
            return data["results"][0]["artworkUrl100"].replace("100x100", "600x600")

        return None

    except:
        return None

# ======================
# START
# ======================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(
            f"❌ Подпишитесь на {CHANNEL_USERNAME}\n\n"
            "После этого нажмите /start"
        )
        return

    await message.answer(
        "🎵 <b>Добро пожаловать!</b>\n\n"
        "Как пользоваться:\n"
        "1️⃣ Нажми «🎵 Распознать музыку»\n"
        "2️⃣ Отправь голосовое или кружок\n"
        "3️⃣ Получи название + ссылки\n\n"
        "⭐ Можно добавлять в избранное",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# ======================
# КНОПКИ МЕНЮ (ВАЖНО - ФИКС)
# ======================
@dp.message_handler(lambda m: m.text == "🎵 Распознать музыку")
async def ask_music(message: types.Message):
    await message.answer("🎧 Отправь голосовое, кружок или аудио")

@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def show_favorites(message: types.Message):
    fav = favorites.get(message.from_user.id, [])

    if not fav:
        await message.answer("⭐ Избранное пустое")
        return

    text = "⭐ <b>Избранное:</b>\n\n" + "\n".join(fav)
    await message.answer(text, parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "📜 История")
async def show_history(message: types.Message):
    hist = history.get(message.from_user.id, [])

    if not hist:
        await message.answer("📜 История пуста")
        return

    text = "📜 <b>Последние треки:</b>\n\n" + "\n".join(hist[-10:])
    await message.answer(text, parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "🎵 Нажмите «Распознать музыку»\n"
        "🎤 Отправьте голосовое или кружок\n"
        "🎧 Получите название трека\n\n"
        "⭐ Добавляйте в избранное\n"
        "📜 Смотрите историю",
        parse_mode="HTML"
    )

# ======================
# ИЗБРАННОЕ (INLINE)
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
        await message.answer(f"❌ Подпишитесь на {CHANNEL_USERNAME}")
        return

    await message.answer("🎧 Распознаю...")

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

        if result.get("result"):

            artist = result["result"]["artist"]
            title = result["result"]["title"]

            text = f"🎵 {artist} - {title}"

            image = get_cover(artist, title)
            kb = make_links(artist, title)

            history.setdefault(message.from_user.id, [])
            history[message.from_user.id].append(text)

            if image:
                await bot.send_photo(
                    message.chat.id,
                    photo=image,
                    caption=text,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            else:
                await message.answer(text, reply_markup=kb)

        else:
            await message.answer("❌ Не удалось распознать")

    except Exception as e:
        print(e)
        await message.answer("❌ Ошибка обработки")

# ======================
# RUN
# ======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)