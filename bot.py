import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI ---
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))
WIB = timezone(timedelta(hours=7))
DATA_FILE = "boss_data.json"

# --- SETUP GOOGLE SHEETS ---
creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- FUNGSI PERSISTENSI ---
def simpan_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def muat_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

# --- MONITORING TASKS ---
@tasks.loop(minutes=1)
async def monitor_boss():
    now = datetime.now(WIB).replace(tzinfo=None)
    data = muat_data()
    to_remove = []
    channel = bot.get_channel(CHANNEL_ID)
    
    for boss, spawn_str in data.items():
        spawn_time = datetime.fromisoformat(spawn_str).replace(tzinfo=None)
        if spawn_time <= now:
            if channel: await channel.send(f"⚔️ Boss **{boss.capitalize()}** sudah spawn!")
            to_remove.append(boss)
            
    for boss in to_remove: del data[boss]
    if to_remove: simpan_data(data)

@tasks.loop(minutes=1)
async def monitor_fix_boss():
    now = datetime.now(WIB)
    current_day = now.strftime("%A")
    current_time = now.strftime("%H:%M")
    try:
        data = client.open("Master Boss timer").worksheet("fix").get_values("A4:C35")
        for row in data:
            if len(row) >= 3 and current_day.lower() in row[0].lower():
                if row[1].split('/')[0].strip() == current_time:
                    channel = bot.get_channel(CHANNEL_ID)
                    if channel: await channel.send(f"@everyone 📢 **FIX BOSS ALERT!** Sekarang spawn: **{row[2]}**")
    except Exception as e: print(f"Error Fix: {e}")

# --- COMMANDS ---
@bot.command()
async def startboss(ctx, nama: str, menit: int):
    data = muat_data()
    data[nama.lower()] = (datetime.now(WIB) + timedelta(minutes=menit)).isoformat()
    simpan_data(data)
    await ctx.send(f"✅ Pengingat **{nama}** disetel ({menit} menit lagi).")

@bot.command()
async def status(ctx):
    data = muat_data()
    if not data:
        await ctx.send("✅ Tidak ada boss yang sedang dipantau.")
        return
    
    now_wib = datetime.now(WIB).replace(tzinfo=None)
    pesan = "⚔️ **JADWAL BOSS**\n"
    
    for nama, waktu_str in data.items():
        waktu_spawn = datetime.fromisoformat(waktu_str).replace(tzinfo=None)
        sisa = int((waktu_spawn - now_wib).total_seconds() / 60)
        
        if sisa < 0: continue
        
        waktu_wib = waktu_spawn.strftime("%H:%M")
        waktu_pht = (waktu_spawn + timedelta(hours=1)).strftime("%H:%M")
        pesan += (f"**{nama.capitalize()}**\n"
                  f"  > 🇮🇩 {waktu_wib} WIB | 🇵🇭 {waktu_pht} PHT\n"
                  f"  > ⏳ {sisa}m lagi\n")
    await ctx.send(pesan)

@bot.command()
async def fixlist(ctx):
    try:
        now = datetime.now(WIB)
        current_day = now.strftime("%A")
        data = client.open("Master Boss timer").worksheet("fix").get_values("A4:C35")
        pesan = f"📅 **Jadwal Fix Boss Hari Ini ({current_day}):**\n"
        found = False
        for row in data:
            if len(row) >= 3 and current_day.lower() in row[0].lower():
                pesan += f"- {row[1]} | **{row[2]}**\n"
                found = True
        if not found: pesan += "Tidak ada jadwal untuk hari ini."
        await ctx.send(pesan)
    except Exception as e: await ctx.send(f"❌ Gagal: {e}")

@bot.event
async def on_ready():
    monitor_boss.start()
    monitor_fix_boss.start()
    print(f'✅ Bot Ready: {bot.user}')

bot.run(TOKEN)
