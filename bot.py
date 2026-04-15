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
    "Напиши название города и я пришлю прогноз на сегодня и ближайшие 10 дней:\n\n"
    "Примеры:\n"
    "• Москва\n"
    "• Нальчик\n"
    "• Нью-Йорк\n\n"
    "🌙 Все сервисы Luna: @LunaHub"
)

WIND_DIR = {
    "N": "⬆️", "NE": "↗️", "E": "➡️", "SE": "↘️",
    "S": "⬇️", "SW": "↙️", "W": "⬅️", "NW": "↖️"
}


def get_emoji(code: int) -> str:
    if code == 1000: return "☀️"
    if code in [1003, 1006]: return "⛅"
    if code in [1009]: return "☁️"
    if code in [1030, 1135, 1147]: return "🌫️"
    if code in [1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195]: return "🌧️"
    if code in [1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225]: return "❄️"
    if code in [1087, 1273, 1276]: return "⛈️"
    return "🌡️"


async def get_forecast(city: str) -> str:
    url = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": WEATHER_API,
        "q": city,
        "days": 10,
        "lang": "ru",
        "aqi": "no",
        "alerts": "no",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 400:
                return None
            data = await resp.json()

    loc = data["location"]
    cur = data["current"]
    forecast_days = data["forecast"]["forecastday"]

    city_name = loc["name"]
    country = loc["country"]

    # Сегодняшняя погода подробно
    code = cur["condition"]["code"]
    emoji = get_emoji(code)
    temp = cur["temp_c"]
    feels = cur["feelslike_c"]
    humidity = cur["humidity"]
    wind = cur["wind_kph"]
    wind_dir = WIND_DIR.get(cur["wind_dir"], "")
    desc = cur["condition"]["text"]
    pressure = round(cur["pressure_mb"] * 0.750064)

    lines = [
        f"📍 <b>{city_name}, {country}</b>",
        f"",
        f"{emoji} <b>Сейчас: {temp:+.0f}°C</b> — {desc}",
        f"🤔 Ощущается как {feels:+.0f}°C",
        f"💧 Влажность: {humidity}% | 💨 Ветер: {wind_dir} {wind} км/ч",
        f"🔘 Давление: {pressure} мм рт.ст.",
        f"",
        f"<b>📅 Прогноз на 10 дней:</b>",
    ]

    # Прогноз по дням
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    months_ru = ["", "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

    for i, day in enumerate(forecast_days):
        date_parts = day["date"].split("-")
        month = int(date_parts[1])
        d = int(date_parts[2])

        import datetime
        dt = datetime.date(int(date_parts[0]), month, d)
        day_name = days_ru[dt.weekday()]

        day_data = day["day"]
        max_t = day_data["maxtemp_c"]
        min_t = day_data["mintemp_c"]
        day_code = day_data["condition"]["code"]
        day_emoji = get_emoji(day_code)
        rain_chance = day_data.get("daily_chance_of_rain", 0)

        if i == 0:
            prefix = "Сегодня  "
        elif i == 1:
            prefix = "Завтра    "
        else:
            prefix = f"{day_name} {d} {months_ru[month]}  "

        rain_str = f" 💧{rain_chance}%" if rain_chance > 20 else ""
        lines.append(f"{day_emoji} <b>{prefix}</b> {max_t:+.0f}° / {min_t:+.0f}°{rain_str}")

    lines.append("")
    lines.append("🌙 <i>LunaWeather • @LunaHub</i>")

    return "\n".join(lines)


@dp.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(WELCOME)


@dp.message(F.text)
async def handle_city(msg: Message):
    city = msg.text.strip()
    wait = await msg.answer("🔍 Загружаю прогноз...")

    result = await get_forecast(city)
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
