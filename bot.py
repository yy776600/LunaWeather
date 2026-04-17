import asyncio
import logging
import os
import datetime
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
    "🌤 Привет! Я LunaWeather!\n\n"
    "Напиши название города и получишь:\n"
    "• Подробную погоду прямо сейчас\n"
    "• Прогноз на каждый из 10 дней\n\n"
    "Примеры: Москва, Нальчик, Грозный\n\n"
    "🌙 Все сервисы: @LunaHub"
)

DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS_RU = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WIND_DIR = {
    "N": "⬆️ Север", "NE": "↗️ Северо-восток", "E": "➡️ Восток",
    "SE": "↘️ Юго-восток", "S": "⬇️ Юг", "SW": "↙️ Юго-запад",
    "W": "⬅️ Запад", "NW": "↖️ Северо-запад"
}


def get_emoji(code: int) -> str:
    if code == 1000: return "☀️"
    if code in [1003]: return "🌤"
    if code in [1006]: return "⛅"
    if code in [1009]: return "☁️"
    if code in [1030, 1135, 1147]: return "🌫️"
    if code in [1063, 1150, 1153, 1180, 1183]: return "🌦️"
    if code in [1186, 1189, 1192, 1195, 1198, 1201]: return "🌧️"
    if code in [1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225]: return "❄️"
    if code in [1087, 1273, 1276, 1279, 1282]: return "⛈️"
    return "🌡️"


def uv_desc(uv: float) -> str:
    if uv <= 2: return "Низкий"
    if uv <= 5: return "Умеренный"
    if uv <= 7: return "Высокий"
    if uv <= 10: return "Очень высокий"
    return "Экстремальный"


async def fetch_weather(query: str) -> dict | None:
    url = "http://api.weatherapi.com/v1/forecast.json"
    params = {"key": WEATHER_API, "q": query, "days": 10, "lang": "ru", "aqi": "no"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 400:
                return None
            return await resp.json()


async def get_forecast(city: str) -> tuple:
    # Сначала пробуем с Россией
    data = await fetch_weather(f"{city}, RU")
    # Если не нашли — пробуем без страны
    if not data:
        data = await fetch_weather(city)
    if not data:
        return None, None

    loc = data["location"]
    cur = data["current"]
    days = data["forecast"]["forecastday"]

    city_name = loc["name"]
    country = loc["country"]
    local_time = loc["localtime"].split(" ")[1]

    code = cur["condition"]["code"]
    emoji = get_emoji(code)
    temp = cur["temp_c"]
    feels = cur["feelslike_c"]
    humidity = cur["humidity"]
    wind_kph = cur["wind_kph"]
    wind_dir = WIND_DIR.get(cur["wind_dir"], cur["wind_dir"])
    pressure = round(cur["pressure_mb"] * 0.750064)
    visibility = cur["vis_km"]
    uv = cur["uv"]
    desc = cur["condition"]["text"]
    cloud = cur["cloud"]
    sunrise = days[0]["astro"]["sunrise"]
    sunset = days[0]["astro"]["sunset"]

    now_text = (
        f"📍 <b>{city_name}, {country}</b>  🕐 {local_time}\n"
        f"{'─' * 28}\n"
        f"{emoji} <b>{temp:+.0f}°C</b>  •  {desc}\n"
        f"🤔 Ощущается: <b>{feels:+.0f}°C</b>\n"
        f"💧 Влажность: <b>{humidity}%</b>\n"
        f"💨 Ветер: <b>{wind_kph:.0f} км/ч</b> {wind_dir}\n"
        f"🔘 Давление: <b>{pressure} мм рт.ст.</b>\n"
        f"👁 Видимость: <b>{visibility} км</b>\n"
        f"☁️ Облачность: <b>{cloud}%</b>\n"
        f"☀️ УФ: <b>{uv:.0f}</b> — {uv_desc(uv)}\n"
        f"🌅 {sunrise}  🌇 {sunset}"
    )

    forecast_text = f"📅 <b>Прогноз на 10 дней — {city_name}</b>\n{'─' * 28}\n"

    for i, day in enumerate(days):
        y, m, d = map(int, day["date"].split("-"))
        dt = datetime.date(y, m, d)
        day_name = DAYS_RU[dt.weekday()]
        month_name = MONTHS_RU[m]
        dd = day["day"]
        max_t = dd["maxtemp_c"]
        min_t = dd["mintemp_c"]
        avg_t = dd["avgtemp_c"]
        rain = dd.get("daily_chance_of_rain", 0)
        snow = dd.get("daily_chance_of_snow", 0)
        wind_max = dd["maxwind_kph"]
        humidity_avg = dd["avghumidity"]
        uv_day = dd["uv"]
        day_desc = dd["condition"]["text"]
        day_emoji = get_emoji(dd["condition"]["code"])
        sr = day["astro"]["sunrise"]
        ss = day["astro"]["sunset"]
        label = "Сегодня" if i == 0 else "Завтра" if i == 1 else day_name
        precip = f"🌨 Снег: {snow}%" if snow > 20 else (f"🌧 Дождь: {rain}%" if rain > 20 else "")

        forecast_text += (
            f"\n{day_emoji} <b>{label}, {d} {month_name}</b>\n"
            f"🌡 {max_t:+.0f}° / {min_t:+.0f}°  •  {day_desc}\n"
            f"🌡 Средняя: {avg_t:+.0f}°  •  ☀️ УФ: {uv_day:.0f}\n"
            f"💨 до {wind_max:.0f} км/ч  •  💧 {humidity_avg:.0f}%\n"
            f"🌅 {sr}  🌇 {ss}\n"
        )
        if precip:
            forecast_text += f"{precip}\n"
        forecast_text += "─" * 28 + "\n"

    forecast_text += "\n🌙 <i>LunaWeather • @LunaHub</i>"
    return now_text, forecast_text


@dp.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(WELCOME)


@dp.message(F.text)
async def handle_city(msg: Message):
    city = msg.text.strip()
    wait = await msg.answer("🔍 Загружаю прогноз...")
    now_text, forecast_text = await get_forecast(city)
    await wait.delete()
    if not now_text:
        await msg.answer("❌ Город не найден. Попробуй написать по-другому.")
        return
    await msg.answer(now_text, parse_mode="HTML")
    await msg.answer(forecast_text, parse_mode="HTML")


async def main():
    logging.info("LunaWeather запущен!")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
