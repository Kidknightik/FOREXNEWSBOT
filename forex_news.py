import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
import requests
import time
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import datetime

# NOTE: per request, token is stored directly in code (not recommended for production).
TOKEN = ""

# Configure these to your guild/channel
GUILD_ID =        # ID сервера (int)
CHANNEL_ID =      # Канал, куда писать "бот онлайн" (int)

# Intents: ensure guilds/messages are enabled so the bot can find channels
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)


### ---------- Получение и парсинг данных (Investing.com) ----------
def get_forex_data(period="today"):
    """Parse investing.com calendar for today/tomorrow/week. Returns dict: {'events': [...], 'error': str|None}"""
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime, timedelta
    url = "https://www.investing.com/economic-calendar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr.js-event-item")
        events = []
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        week_dates = [today + timedelta(days=i) for i in range(7)]
        for row in rows:
            # Date/time
            time_cell = row.select_one("td.time")
            time_str = time_cell.get_text(strip=True) if time_cell else ""
            # Country
            country_cell = row.select_one("td.flag")
            country = country_cell.get("title") if country_cell and country_cell.get("title") else ""
            # Impact
            impact_cell = row.select_one("td.sentiment")
            impact = impact_cell.get("data-img_key") if impact_cell and impact_cell.get("data-img_key") else "Low"
            # Title
            event_cell = row.select_one("td.event")
            title = event_cell.get_text(strip=True) if event_cell else "No title"
            # Forecast/Previous/Actual
            forecast_cell = row.select_one("td.forecast")
            forecast = forecast_cell.get_text(strip=True) if forecast_cell else "—"
            previous_cell = row.select_one("td.previous")
            previous = previous_cell.get_text(strip=True) if previous_cell else "—"
            actual_cell = row.select_one("td.actual")
            actual = actual_cell.get_text(strip=True) if actual_cell else "—"
            # Date logic
            date_cell = row.select_one("td.date")
            date_str = date_cell.get_text(strip=True) if date_cell else ""
            event_date = today
            if date_str:
                try:
                    event_date = datetime.strptime(date_str, "%b %d, %Y").date()
                except Exception:
                    event_date = today
            # Filter by period
            if period == "today" and event_date != today:
                continue
            if period == "tomorrow" and event_date != tomorrow:
                continue
            if period == "week" and event_date < today:
                continue
            if period == "week" and event_date > today + timedelta(days=6):
                continue
            events.append({
                "date": str(event_date),
                "time": time_str,
                "impact": impact,
                "title": title,
                "country": country,
                "forecast": forecast if forecast else "—",
                "previous": previous if previous else "—",
                "actual": actual if actual else "—",
            })
        return {"events": events, "error": None}
    except Exception as e:
        print("Ошибка при парсинге investing.com:", e)
        return {"events": [], "error": str(e)}


# ---------- Форматирование Embed ----------
def format_forex_embed(period, data):
    embed = discord.Embed(
        title=f"📊 Forex News {period.capitalize()}",
        color=discord.Color.blurple(),
        timestamp=datetime.datetime.utcnow()
    )

    if not data:
        embed.description = "❌ Нет важных событий."
        return embed

    # Group by impact (from investing.com: bull1, bull2, bull3)
    impact_map = {
        "bull3": "🔴 High impact",
        "bull2": "🟠 Medium impact",
        "bull1": "🟢 Low impact",
        "Low": "🟢 Low impact",
        "": "🟢 Low impact"
    }
    grouped = {"bull3": [], "bull2": [], "bull1": []}

    for event in data:
        imp = event.get("impact", "bull1")
        if imp not in grouped:
            imp = "bull1"
        grouped[imp].append(event)

    def country_flag(code: str) -> str:
        # Try to convert country name to flag emoji (simple mapping for common cases)
        flags = {
            "United States": "🇺🇸", "Japan": "🇯🇵", "United Kingdom": "🇬🇧", "Germany": "🇩🇪", "France": "🇫🇷", "Canada": "🇨🇦", "Australia": "🇦🇺", "China": "🇨🇳", "Switzerland": "🇨🇭", "Euro Zone": "🇪🇺"
        }
        return flags.get(code, "")

    for imp in ["bull3", "bull2", "bull1"]:
        events = grouped[imp]
        if not events:
            continue
        lines = []
        for e in events[:6]:
            flag = country_flag(e.get("country", ""))
            name = e.get("title", "No title")
            date = e.get("date", "")
            time = e.get("time", "")
            forecast = e.get("forecast", "—") or "—"
            previous = e.get("previous", "—") or "—"
            actual = e.get("actual", "—") or "—"
            # Always show all three stats, even if missing
            lines.append(f"{flag} **{name}**\n📅 {date} • 🕒 {time}\n📊 Actual: `{actual}` | Forecast: `{forecast}` | Previous: `{previous}`")
        embed.add_field(name=f"{impact_map.get(imp, imp)}", value="\n\n".join(lines), inline=False)

    embed.set_footer(text="Powered by Investing.com")
    return embed


# ---------- Slash-команды ----------
@bot.tree.command(name="today", description="Показать важные новости Forex за сегодня", guild=discord.Object(id=GUILD_ID))
async def today(interaction: discord.Interaction):
    await interaction.response.defer()
    res = get_forex_data("today")
    if res.get('error') and not res.get('cached'):
        await interaction.followup.send("❌ Не удалось получить данные с API. Попробуйте позже.")
        return
    data = res.get('events', [])
    embed = format_forex_embed("today", data)
    if res.get('cached'):
        embed.set_footer(text=(embed.footer.text + " — (cached data)" if embed.footer and embed.footer.text else "(cached data)"))
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="tomorrow", description="Показать важные новости Forex на завтра", guild=discord.Object(id=GUILD_ID))
async def tomorrow(interaction: discord.Interaction):
    await interaction.response.defer()
    res = get_forex_data("tomorrow")
    if res.get('error') and not res.get('cached'):
        await interaction.followup.send("❌ Не удалось получить данные с API. Попробуйте позже.")
        return
    data = res.get('events', [])
    embed = format_forex_embed("tomorrow", data)
    if res.get('cached'):
        embed.set_footer(text=(embed.footer.text + " — (cached data)" if embed.footer and embed.footer.text else "(cached data)"))
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="week", description="Показать новости Forex на неделю", guild=discord.Object(id=GUILD_ID))
async def week(interaction: discord.Interaction):
    await interaction.response.defer()
    res = get_forex_data("week")
    if res.get('error') and not res.get('cached'):
        await interaction.followup.send("❌ Не удалось получить данные с API. Попробуйте позже.")
        return
    data = res.get('events', [])
    embed = format_forex_embed("week", data)
    if res.get('cached'):
        embed.set_footer(text=(embed.footer.text + " — (cached data)" if embed.footer and embed.footer.text else "(cached data)"))
    await interaction.followup.send(embed=embed)


# ---------- Событие запуска ----------
@bot.event
async def on_ready():
    print(f"✅ {bot.user} запущен и готов к работе!")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print("Ошибка при синхронизации команд:", e)
    # Try to get channel from cache first, otherwise fetch from API
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(CHANNEL_ID)
        if channel:
            await channel.send("🟢 **Economic Calendar** запущен и онлайн!")
    except Exception as e:
        print("Не удалось отправить сообщение в канал при старте:", e)


# ---------- Запуск ----------
if __name__ == '__main__':
    bot.run(TOKEN)
