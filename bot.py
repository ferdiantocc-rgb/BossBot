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

# --- PERSISTENT STORAGE (Railway Volume) ---
# Folder ini harus di-mount ke Volume di dasbor Railway
DATA_DIR = "/app/data"
DATA_FILE = os.path.join(DATA_DIR, "boss_data.json")

# Buat folder jika belum ada
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

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

def simpan_data(data):
    try:
        with open(DATA_FILE, "w") as f: json.dump(data, f)
    except Exception as e: print(f"Gagal simpan: {e}")

def muat_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

# --- VIEW TOMBOL ---
class BossDoneView(discord.ui.View):
    def __init__(self, nama_boss):
        super().__init__(timeout=None)
        self.nama_boss = nama_boss

    @discord.ui.button(label="✅ Boss Sudah Mati", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Durasi default jika tidak ada di dict
        menit_durasi = 600 
        data = muat_data()
        data[self.nama_boss.lower()] = (datetime.now(WIB) + timedelta(minutes=menit_durasi)).isoformat()
        simpan_data(data)
        await interaction.response.send_message(f"✅ {self.nama_boss.capitalize()} di-reset.")
        button.disabled = True
        await interaction.message.edit(view=self)

# --- TASKS MONITORING ---
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
            if channel: await channel.send(f"@everyone ⚠️ Boss **{boss.capitalize()}** spawn {sisa} menit lagi!", allowed_mentions=discord.AllowedMentions.all())
            notifikasi_sent[boss][str(sisa)] = True
        elif sisa <= 0:
            if channel: await channel.send(f"⚔️ Boss **{boss.capitalize()}** sudah spawn!", view=BossDoneView(boss))
            to_remove.append(boss)
            if boss in notifikasi_sent: del notifikasi_sent[boss]
            
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
                    await channel.send(f"@everyone ⚠️ Fix Boss **{row[2]}** spawn {sisa} menit lagi!", allowed_mentions=discord.AllowedMentions.all())
                    notifikasi_fix[key][str(sisa)] = True
                elif sisa == 0:
                    await channel.send(f"@everyone 📢 **FIX BOSS ALERT!** Sekarang spawn: **{row[2]}**", allowed_mentions=discord.AllowedMentions.all())
    except: pass

# --- COMMANDS ---
@bot.command()
async def status(ctx):
    data = muat_data()
    if not data: await ctx.send("✅ Tidak ada boss yang dipantau.")
    else:
        now = datetime.now(WIB).replace(tzinfo=None)
        pesan = "⚔️ **JADWAL BOSS**\n```fix\n"
        for nama, waktu_str in data.items():
            spawn = datetime.fromisoformat(waktu_str).replace(tzinfo=None)
            diff = spawn - now
            mins = int(diff.total_seconds() / 60)
            pesan += f"{nama.capitalize():<15} | ⏳ {mins}m lagi\n"
        pesan += "```"
        await ctx.send(pesan)

@bot.event
async def on_ready():
    monitor_boss.start()
    monitor_fix_boss.start()
    print(f'✅ Bot Ready: {bot.user}')

bot.run(TOKEN)
