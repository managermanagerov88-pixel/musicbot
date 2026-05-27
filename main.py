import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

BOT_TOKEN = "ВСТАВЬ_ТОКЕН_ОТ_BOTFATHER"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🎵 Бот работает! Отправь аудио или голосовое.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp)