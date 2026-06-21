import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI ---
TOKEN = os.getenv('DISCORD_TOKEN')
DB_FILE = 'database.json'
WIB = timezone(timedelta(hours=7))

# --- SETUP GOOGLE SHEETS (DARI RAILWAY VARIABLE) ---
# Pastikan Anda sudah mengisi GOOGLE_CREDENTIALS di Railway Variables
creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Master Boss timer").worksheet("database_backup")

# --- DATA BOSS ---
DATA_BOSS = {
    "Venatus": 10, "Viorent": 10, "LadyDalia": 18, "Ego": 21, "Shuliar": 35, 
    "Larba": 35, "Catena": 35, "Livera": 24, "Undomiel": 24, "Araneo": 24, 
    "Wannitas": 48, "Metus": 48, "Duplican": 48, "BaronBraudmore": 32, 
    "Gareth": 32, "Amentis": 29, "Titore": 37, "GeneralAquleus": 29,
    "Ordo": 62, "Asta": 62, "Secreta": 62, "Supore": 62,
}

boss_aktif = {}
CHANNEL_ID = None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- FUNGSI BACKUP ---
def backup_ke_sheets():
    try:
        with open(DB_FILE, 'r') as f:
            data_string = f.read()
        sheet.update('A2', [[data_string]])
    except Exception as e:
        print(f"Gagal backup: {e}")

def ambil_dari_sheets():
    try:
        data_string = sheet.acell('A2').value
        if data_string:
            with open(DB_FILE, 'w') as f:
                f.write(data_string)
    except Exception as e:
        print(f"Gagal ambil dari Sheets: {e}")

# --- LOGIKA DATABASE ---
def simpan_db():
    data = {
        "channel_id": CHANNEL_ID,
        "boss_aktif": {k: v.isoformat() for k, v in boss_aktif.items()}
    }
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)
    backup_ke_sheets()

def muat_db():
    global CHANNEL_ID, boss_aktif
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                CHANNEL_ID = data.get("channel_id")
                boss_aktif = {k: datetime.fromisoformat(v) for k, v in data.get("boss_aktif", {}).items()}
        except: pass

@bot.event
async def on_ready():
    ambil_dari_sheets() # Pastikan data terbaru dari Sheets saat startup
    muat_db()
    print(f'✅ Bot Ready: {bot.user}')

@bot.command()
async def startboss(ctx, nama_boss: str):
    global CHANNEL_ID
    CHANNEL_ID = ctx.channel.id
    nama_resmi = next((b for b in DATA_BOSS if b.lower() == nama_boss.lower()), None)
    if nama_resmi:
        await ctx.send(f"Berapa menit lagi **{nama_resmi}** spawn?")
        def check(m): return m.author == ctx.author and m.content.isdigit()
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            boss_aktif[nama_resmi] = datetime.now(WIB) + timedelta(minutes=int(msg.content))
            simpan_db()
            await ctx.send(f"✅ Pengingat **{nama_resmi}** disetel.")
        except: await ctx.send("❌ Input tidak valid.")
    else: await ctx.send("❌ Boss tidak ditemukan.")

bot.run(TOKEN)
