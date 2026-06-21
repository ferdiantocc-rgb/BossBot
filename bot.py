import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))
WIB = timezone(timedelta(hours=7))

# --- PATH PERSISTENT ---
DATA_DIR = "/app/data"
DATA_FILE = os.path.join(DATA_DIR, "boss_data.json")

# Pastikan folder ada dan bisa ditulis
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        print(f"Error membuat folder: {e}")

# --- SETUP BOT ---
creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- FUNGSI DATA (DIPERBAIKI) ---
def simpan_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Gagal simpan: {e}")

def muat_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except: return {}

# --- COMMANDS ---
@bot.command()
async def startboss(ctx, nama: str, menit: int):
    data = muat_data()
    data[nama.lower()] = (datetime.now(WIB) + timedelta(minutes=menit)).isoformat()
    simpan_data(data)
    await ctx.send(f"✅ **{nama.capitalize()}** disetel ({menit} menit).")

@bot.command()
async def status(ctx):
    data = muat_data()
    if not data: 
        await ctx.send("✅ Tidak ada boss yang dipantau.")
    else:
        now = datetime.now(WIB).replace(tzinfo=None)
        pesan = "⚔️ **JADWAL BOSS**\n```fix\n"
        for nama, waktu_str in data.items():
            spawn = datetime.fromisoformat(waktu_str).replace(tzinfo=None)
            diff = int((spawn - now).total_seconds() / 60)
            pesan += f"{nama.capitalize():<12} | ⏳ {max(0, diff)}m lagi\n"
        pesan += "```"
        await ctx.send(pesan)

@bot.event
async def on_ready():
    print(f'✅ Bot Ready: {bot.user}')
    # Pastikan task dijalankan
    if not monitor_boss.is_running(): monitor_boss.start()
    if not monitor_fix_boss.is_running(): monitor_fix_boss.start()

# ... (Pastikan monitor_boss dan monitor_fix_boss ada di sini)
bot.run(TOKEN)
