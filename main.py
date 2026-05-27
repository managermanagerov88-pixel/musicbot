import logging
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ======================
# НАСТРОЙКИ
# ======================
BOT_TOKEN = "8994533338:AAEouqVsEXkiRLViw2I1RucsEkKswUZP5RY"
AUDD_API_KEY = "5eeedf20b79da84a763484f3358ad40b"
CHANNEL_USERNAME = "@sp_rap"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ======================
# ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ
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
def menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("🎵 Распознать музыку")
    kb.add("⭐ Избранное", "📜 История")
    kb.add("ℹ️ Помощь")

    return kb

# ======================
# ССЫЛКИ
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

    kb.add(
        InlineKeyboardButton("⭐ В избранное", callback_data=f"fav|{artist} - {title}")
    )

    return kb

# ======================
# 🔥 ОБЛОЖКА (СТАБИЛЬНАЯ)
# ======================
def get_cover(result):
    # Apple Music (лучший источник)
    try:
        if result.get("apple_music"):
            img = result["apple_music"]["artwork"]["url"]
            return img.replace("{w}x{h}", "600x600")
    except:
        pass

    # Deezer
    try:
        if result.get("deezer"):
            return result["deezer"]["album"]["cover_big"]
    except:
        pass

    # AudD fallback
    return result.get("album_image") or result.get("image")

# ======================
# START
# ======================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(f"❌ Подпишитесь на {CHANNEL_USERNAME}")
        return

    await message.answer(
        "🎵 <b>Music Bot запущен</b>\n\n"
        "Отправь:\n"
        "🎤 голосовое\n🔵 кружок\n🎧 аудио",
        parse_mode="HTML",
        reply_markup=menu()
    )

# ======================
# КНОПКИ ИЗБРАННОГО
# ======================
@dp.callback_query_handler(lambda c: c.data.startswith("fav|"))
async def fav(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    song = callback.data.split("|")[1]

    favorites.setdefault(user_id, [])
    favorites[user_id].append(song)

    await callback.answer("Добавлено ⭐")

# ======================
# МЕНЮ КНОПКИ
# ======================
@dp.message_handler(lambda m: m.text == "⭐ Избранное")
async def show_fav(message: types.Message):
    fav = favorites.get(message.from_user.id, [])

    if not fav:
        await message.answer("⭐ Пусто")
        return

    await message.answer("\n".join(fav))

@dp.message_handler(lambda m: m.text == "📜 История")
async def show_history(message: types.Message):
    hist = history.get(message.from_user.id, [])

    if not hist:
        await message.answer("📜 Пусто")
        return

    await message.answer("\n".join(hist[-10:]))

@dp.message_handler(lambda m: m.text == "ℹ️ Помощь")
async def help_msg(message: types.Message):
    await message.answer(
        "🎵 Просто отправь голосовое или кружок\n"
        "и я найду музыку"
    )

# ======================
# РАСПОЗНАВАНИЕ
# ======================
@dp.message_handler(content_types=['voice', 'audio', 'video_note'])
async def music(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(f"❌ Подпишитесь на {CHANNEL_USERNAME}")
        return

    await message.answer("🎧 Ищу трек...")

    try:
        # файл
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        else:
            file_id = message.video_note.file_id

        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        # AudD
        data = {
            "api_token": AUDD_API_KEY,
            "url": file_url
        }

        r = requests.post("https://api.audd.io/", data=data, timeout=25)
        result = r.json()

        print(result)

        if result.get("result"):

            res = result["result"]

            artist = res["artist"]
            title = res["title"]

            # 🔥 обложка
            image = get_cover(res)

            text = f"🎵 {artist} - {title}"

            kb = make_links(artist, title)

            history.setdefault(message.from_user.id, [])
            history[message.from_user.id].append(text)

            if image:
                await bot.send_photo(
                    message.chat.id,
                    photo=image,
                    caption=text,
                    reply_markup=kb
                )
            else:
                await message.answer(text, reply_markup=kb)

        else:
            await message.answer("❌ Не найдено")

    except Exception as e:
        print("ERROR:", e)
        await message.answer("❌ Ошибка обработки")

# ======================
# RUN
# ======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)