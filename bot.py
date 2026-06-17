import discord
from discord.ext import commands
import requests
import os
import pytz
from datetime import datetime

# Bot akan mengambil URL langsung dari variabel SHEET_URL yang ada di Railway
SHEET_URL = os.environ.get('SHEET_URL')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def status(ctx):
    """Mengecek status boss interval"""
    if not SHEET_URL:
        await ctx.send("⚠️ Error: SHEET_URL belum diatur di Railway.")
        return
        
    try:
        response = requests.get(SHEET_URL).json()
        data = response['interval']
        msg = "**📊 Status Boss (Interval):**\n"
        for row in data[1:]: # Skip header
            if row[0]: # Nama boss
                # Sesuaikan index jika urutan kolom di Sheet Anda berbeda
                msg += f"• **{row[0]}** | Mati: {row[2]} | Respawn: {row[3]}\n"
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"Error mengambil status: {e}")

@bot.command()
async def list_fix(ctx):
    """Mengecek jadwal boss tetap"""
    if not SHEET_URL:
        await ctx.send("⚠️ Error: SHEET_URL belum diatur di Railway.")
        return

    try:
        response = requests.get(SHEET_URL).json()
        data = response['fix']
        msg = "**📅 Jadwal Boss Tetap:**\n"
        for row in data[1:]:
            if row[2]: # Nama boss
                msg += f"• {row[2]} | 🕒 {row[1]} | 📅 {row[0]}\n"
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"Error mengambil jadwal: {e}")

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} sudah online dan siap!')

# Gunakan TOKEN dari variabel Railway
bot.run(os.environ.get('TOKEN'))
