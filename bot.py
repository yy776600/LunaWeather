import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН")
WEATHER_API = os.getenv("WEATHER_API", "ВАШ_КЛЮЧ")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

WELCOME = (
    "🌤 Привет! Я LunaWeather — твой погодный помощник!\n\n"
    "Просто напиши название своего города и я покажу погоду:\n\n"
    "Примеры:\n"
    "• Москва\n"
    "• Нальчик\n"
    "• Нью-Йорк\n"
)

WIND_DIR = {
    "N": "⬆️ Север", "NE": "↗️ Северо-восток", "E": "➡️ Восток",
    "SE": "↘️ Юго-восток", "S": "⬇️ Юг", "SW": "↙️ Юго-запад",
    "W": "⬅️ Запад", "NW": "↖️ Северо-запад"
}


def get_emoji(code: int) -> str:
    if code == 1000: return "☀️"
    if code in [1003, 1006]: return "⛅"
    if code in [1009]: return "☁️"
    if code in [1030, 1135, 1147]: return "🌫️"
    if code in [1063, 1150, 1153, 1180, 1183]: return "🌦️"
    if code in [1186, 1189, 1192, 1195]: return "🌧️"
    if code in [1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225]: return "❄️"
    if code in [1087, 1273, 1276]: return "⛈️"
    return "🌡️"


async def get_weather(city: str) -> str:
    url = "http://api.weatherapi.com/v1/current.json"
    params = {"key": WEATHER_API, "q": city, "lang": "ru"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 400:
                return None
            data = await resp.json()

    loc = data["location"]
    cur = data["current"]
    code = cur["condition"]["code"]
    emoji = get_emoji(code)
    desc = cur["condition"]["text"]
    temp = cur["temp_c"]
    feels = cur["feelslike_c"]
    humidity = cur["humidity"]
    wind = cur["wind_kph"]
    wind_dir = WIND_DIR.get(cur["wind_dir"], cur["wind_dir"])
    pressure = round(cur["pressure_mb"] * 0.750064)
    uv = cur["uv"]
    city_name = loc["name"]
    country = loc["country"]

    return (
        f"{emoji} <b>Погода в {city_name}, {country}</b>\n\n"
        f"🌡 Температура: <b>{temp:+.0f}°C</b>\n"
        f"🤔 Ощущается как: <b>{feels:+.0f}°C</b>\n"
        f"📋 {desc}\n\n"
        f"💧 Влажность: <b>{humidity}%</b>\n"
        f"💨 Ветер: <b>{wind} км/ч</b> {wind_dir}\n"
        f"🔘 Давление: <b>{pressure} мм рт.ст.</b>\n"
        f"☀️ УФ-индекс: <b>{uv}</b>"
    )


@dp.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(WELCOME)


@dp.message(F.text)
async def handle_city(msg: Message):
    city = msg.text.strip()
    wait = await msg.answer("🔍 Ищу погоду...")

    result = await get_weather(city)
    await wait.delete()

    if not result:
        await msg.answer("❌ Город не найден. Проверь название и попробуй ещё раз.")
        return

    await msg.answer(result, parse_mode="HTML")


async def main():
    logging.info("LunaWeather запущен!")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
