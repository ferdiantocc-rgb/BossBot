import discord
from discord.ext import commands, tasks
import requests
import os
import pytz
from datetime import datetime

# Setup Variabel
SHEET_URL = os.environ.get('SHEET_URL')
TOKEN = os.environ.get('TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0)) # Pastikan tambahkan CHANNEL_ID di Railway

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def clean_time(val):
    if not val: return "-"
    if isinstance(val, str) and "T" in val:
        try: return val.split("T")[1][:5]
        except: return val
    return str(val)

# --- Loop Notifikasi Otomatis ---
@tasks.loop(minutes=1)
async def check_boss_timer():
    if CHANNEL_ID == 0: return
    try:
        response = requests.get(SHEET_URL).json()
        data = response['interval']
        now = datetime.now(pytz.timezone('Asia/Jakarta'))
        channel = bot.get_channel(CHANNEL_ID)
        
        for row in data[1:]:
            if row[0] and row[3]:
                time_str = clean_time(row[3])
                if time_str == "-": continue
                
                # Hitung selisih waktu
                respawn_dt = now.replace(hour=int(time_str.split(':')[0]), minute=int(time_str.split(':')[1]), second=0, microsecond=0)
                diff = (respawn_dt - now).total_seconds() / 60
                
                if 9.5 <= diff <= 10.5:
                    await channel.send(f"@everyone ⚠️ **{row[0]}** akan spawn dalam **10 menit**! 🇮🇩🇵🇭")
                elif 4.5 <= diff <= 5.5:
                    await channel.send(f"@everyone ⚔️ **{row[0]}** akan spawn dalam **5 menit**! Persiapkan diri! 🇮🇩🇵🇭")
    except Exception as e:
        print(f"Error loop: {e}")

# --- Command ---
@bot.command()
async def status(ctx):
    response = requests.get(SHEET_URL).json()
    embed = discord.Embed(title="📊 Status Boss (Interval) 🇮🇩🇵🇭", color=discord.Color.blue())
    for row in response['interval'][1:]:
        if row[0]:
            embed.add_field(name=row[0], value=f"Mati: {clean_time(row[2])} | Respawn: {clean_time(row[3])}", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    check_boss_timer.start()
    print(f'Bot {bot.user.name} online!')

bot.run(TOKEN)
