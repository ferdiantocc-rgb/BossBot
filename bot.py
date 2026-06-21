import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI (DENGAN PENGECEKAN) ---
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN tidak ditemukan di environment variables!")
    exit(1)

DB_FILE = 'database.json'
WIB = timezone(timedelta(hours=7))

# --- SETUP GOOGLE SHEETS ---
try:
    creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_db = client.open("Master Boss timer").worksheet("database_backup")
except Exception as e:
    print(f"❌ ERROR Google Sheets: {e}")

# --- DATA BOSS ---
DATA_BOSS = {
    "Venatus": 10, "Viorent": 10, "LadyDalia": 18, "Ego": 21, "Shuliar": 35, 
    "Larba": 35, "Catena": 35, "Livera": 24, "Undomiel": 24, "Araneo": 24, 
    "Wannitas": 48, "Metus": 48, "Duplican": 48, "BaronBraudmore": 32, 
    "Gareth": 32, "Amentis": 29, "Titore": 37, "GeneralAquleus": 29,
    "Ordo": 62, "Asta": 62, "Secreta": 62, "Supore": 62,
}

boss_aktif = {}
sent_notifications = {}
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- FUNGSI DB ---
def simpan_db():
    try:
        data = {"channel_id": CHANNEL_ID, "boss_aktif": {k: v.isoformat() for k, v in boss_aktif.items()}}
        with open(DB_FILE, 'w') as f: json.dump(data, f)
        sheet_db.update('A2', [[json.dumps(data)]])
    except Exception as e: print(f"Gagal simpan DB: {e}")

def muat_db():
    global CHANNEL_ID, boss_aktif
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                CHANNEL_ID = data.get("channel_id", CHANNEL_ID)
                boss_aktif = {k: datetime.fromisoformat(v) for k, v in data.get("boss_aktif", {}).items()}
        except: pass

# --- MONITORING ---
@tasks.loop(minutes=1)
async def monitor_boss():
    now = datetime.now(WIB).replace(tzinfo=None)
    to_remove = []
    channel = bot.get_channel(CHANNEL_ID)
    
    for boss, spawn_time in boss_aktif.items():
        time_left = (spawn_time - now).total_seconds() / 60
        if 9.5 < time_left < 10.5 and boss not in sent_notifications.get('10', []):
            if channel: await channel.send(f"@everyone ⚠️ Boss **{boss}** spawn dalam 10 menit!")
            sent_notifications.setdefault('10', []).append(boss)
        elif 4.5 < time_left < 5.5 and boss not in sent_notifications.get('5', []):
            if channel: await channel.send(f"@everyone ⚠️ Boss **{boss}** spawn dalam 5 menit!")
            sent_notifications.setdefault('5', []).append(boss)
        elif time_left <= 0:
            if channel: await channel.send(f"⚔️ Boss **{boss}** sudah spawn!")
            to_remove.append(boss)
            
    for boss in to_remove:
        if boss in boss_aktif: del boss_aktif[boss]
    if to_remove: simpan_db()

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
    except Exception as e: print(f"Error Fix Boss: {e}")

# --- COMMANDS ---
@bot.command()
async def startboss(ctx, nama_boss: str, menit: int):
    global CHANNEL_ID
    CHANNEL_ID = ctx.channel.id
    nama_resmi = next((b for b in DATA_BOSS if b.lower() == nama_boss.lower()), None)
    if nama_resmi:
        boss_aktif[nama_resmi] = datetime.now(WIB) + timedelta(minutes=menit)
        simpan_db()
        await ctx.send(f"✅ Pengingat **{nama_resmi}** disetel ({menit} menit lagi).")
    else: await ctx.send("❌ Boss tidak ditemukan.")

@bot.command()
async def status(ctx):
    muat_db() # Paksa reload dari DB sebelum menampilkan
    if not boss_aktif:
        await ctx.send("✅ Tidak ada boss yang sedang dipantau.")
        return
    pesan = "⏳ **Daftar Boss yang dipantau:**\n"
    now = datetime.now(WIB).replace(tzinfo=None)
    for boss, spawn_time in boss_aktif.items():
        menit = int((spawn_time - now).total_seconds() / 60)
        pesan += f"- **{boss}**: {max(0, menit)} menit lagi\n"
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
    muat_db()
    monitor_boss.start()
    monitor_fix_boss.start()
    print(f'✅ Bot Ready: {bot.user}')

bot.run(TOKEN)
