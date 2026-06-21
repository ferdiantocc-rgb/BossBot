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

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

# --- SETUP ---
creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

notifikasi_sent = {}
notifikasi_fix = {}

# --- FUNGSI DATA ---
def simpan_data(data):
    try:
        with open(DATA_FILE, "w") as f: json.dump(data, f)
    except Exception as e: print(f"Gagal simpan: {e}")

def muat_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {}

def format_countdown(menit_total):
    menit_total = max(0, menit_total)
    jam = menit_total // 60
    mnt = menit_total % 60
    return f"{jam}j {mnt}m" if jam > 0 else f"{mnt}m"

# --- TASKS ---
@tasks.loop(minutes=1)
async def monitor_boss():
    now = datetime.now(WIB).replace(tzinfo=None)
    data = muat_data()
    to_remove = []
    channel = bot.get_channel(CHANNEL_ID)
    for boss, spawn_str in data.items():
        spawn_time = datetime.fromisoformat(spawn_str).replace(tzinfo=None)
        sisa = int((spawn_time - now).total_seconds() / 60)
        if boss not in notifikasi_sent: notifikasi_sent[boss] = {"10": False, "5": False}
        if sisa in [10, 5] and not notifikasi_sent[boss][str(sisa)]:
            if channel: await channel.send(f"@everyone ⚠️ Boss **{boss.capitalize()}** spawn {sisa} menit lagi!")
            notifikasi_sent[boss][str(sisa)] = True
        elif sisa <= 0:
            if channel: await channel.send(f"⚔️ Boss **{boss.capitalize()}** sudah spawn!")
            to_remove.append(boss)
    for boss in to_remove: del data[boss]
    if to_remove: simpan_data(data)

@tasks.loop(minutes=1)
async def monitor_fix_boss():
    now = datetime.now(WIB)
    channel = bot.get_channel(CHANNEL_ID)
    try:
        data = client.open("Master Boss timer").worksheet("fix").get_values("A4:C35")
        for row in data:
            if len(row) >= 3 and now.strftime("%A").lower() in row[0].lower():
                jam_fix = datetime.strptime(row[1].split('/')[0].strip(), "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=WIB)
                sisa = int((jam_fix - now).total_seconds() / 60)
                key = f"{row[2]}_{row[1]}"
                if key not in notifikasi_fix: notifikasi_fix[key] = {"10": False, "5": False}
                if sisa in [10, 5] and not notifikasi_fix[key][str(sisa)]:
                    await channel.send(f"@everyone ⚠️ Fix Boss **{row[2]}** spawn {sisa} menit lagi!")
                    notifikasi_fix[key][str(sisa)] = True
    except: pass

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
    if not data: await ctx.send("✅ Tidak ada boss yang dipantau.")
    else:
        now = datetime.now(WIB).replace(tzinfo=None)
        pesan = "⚔️ **JADWAL BOSS**\n"
        for nama, waktu_str in data.items():
            spawn = datetime.fromisoformat(waktu_str).replace(tzinfo=None)
            w_wib = spawn.strftime("%H:%M")
            w_pht = (spawn + timedelta(hours=1)).strftime("%H:%M")
            diff = int((spawn - now).total_seconds() / 60)
            pesan += f"\n**{nama.capitalize()}**\n > 🇮🇩 {w_wib} WIB | 🇵🇭 {w_pht} PHT\n > ⏳ {format_countdown(diff)} lagi\n"
        await ctx.send(pesan)

@bot.command()
async def fixlist(ctx):
    try:
        now = datetime.now(WIB)
        current_day = now.strftime("%A")
        sheet = client.open("Master Boss timer").worksheet("fix")
        data = sheet.get_values("A4:C35")
        pesan = f"📅 **Jadwal Fix ({current_day}):**\n"
        found = False
        for row in data:
            if len(row) >= 3 and current_day.lower() in row[0].lower():
                w_wib = row[1].split('/')[0].strip()
                w_pht = (datetime.strptime(w_wib, "%H:%M") + timedelta(hours=1)).strftime("%H:%M")
                pesan += f"• **{row[2]}**\n  > 🇮🇩 {w_wib} WIB | 🇵🇭 {w_pht} PHT\n"
                found = True
        await ctx.send(pesan if found else "Tidak ada jadwal fix hari ini.")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.event
async def on_ready():
    if not monitor_boss.is_running(): monitor_boss.start()
    if not monitor_fix_boss.is_running(): monitor_fix_boss.start()
    print(f'✅ Bot Ready: {bot.user}')

bot.run(TOKEN)
