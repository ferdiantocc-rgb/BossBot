import discord
from discord.ext import commands
import requests
import os
import pytz
from datetime import datetime

# Mengambil URL dan Token dari Railway Variables
SHEET_URL = os.environ.get('SHEET_URL')
TOKEN = os.environ.get('TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Fungsi untuk membersihkan format waktu agar tampil HH:MM
def clean_time(val):
    if not val: return "-"
    # Jika data berupa string timestamp panjang (format ISO)
    if isinstance(val, str) and "T" in val:
        try:
            return val.split("T")[1][:5]
        except:
            return val
    # Jika data sudah dalam format waktu/angka
    return str(val)

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
                death_time = clean_time(row[2])
                respawn_time = clean_time(row[3])
                msg += f"• **{row[0]}** | Mati: {death_time} | Respawn: {respawn_time}\n"
                
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

bot.run(TOKEN)
