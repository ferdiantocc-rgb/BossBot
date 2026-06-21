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

DURASI_BOSS = {
    "venatus": 10, "viorent": 10, "ladydalia": 18, "ego": 21, "shuliar": 35, 
    "larba": 35, "catena": 35, "livera": 24, "undomiel": 24, "araneo": 24, 
    "wannitas": 48, "metus": 48, "duplican": 48, "baronbraudmore": 32, 
    "gareth": 32, "amentis": 29, "titore": 37, "generalaquleus": 29,
    "ordo": 62, "asta": 62, "secreta": 62, "supore": 62
}

# --- SETUP ---
creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- TOMBOL BOSS MATI ---
class BossDoneView(discord.ui.View):
    def __init__(self, nama_boss):
        super().__init__(timeout=None)
        self.nama_boss = nama_boss

    @discord.ui.button(label="✅ Boss Sudah Mati", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        durasi = DURASI_BOSS.get(self.nama_boss.lower(), 10)
        data = muat_data()
        data[self.nama_boss.lower()] = (datetime.now(WIB) + timedelta(minutes=durasi)).isoformat()
        simpan_data(data)
        
        await interaction.response.send_message(f"✅ Reset countdown untuk **{self.nama_boss.capitalize()}** ({durasi} menit lagi).", ephemeral=False)
        button.disabled = True
        await interaction.message.edit(view=self)

# --- FUNGSI DATA ---
def simpan_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

def muat_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

# --- MONITORING ---
@tasks.loop(minutes=1)
async def monitor_boss():
    now = datetime.now(WIB).replace(tzinfo=None)
    data = muat_data()
    to_remove = []
    channel = bot.get_channel(CHANNEL_ID)
    
    for boss, spawn_str in data.items():
        spawn_time = datetime.fromisoformat(spawn_str).replace(tzinfo=None)
        if spawn_time <= now:
            # Kirim pesan dengan tombol
            view = BossDoneView(boss)
            if channel: 
                await channel.send(f"⚔️ Boss **{boss.capitalize()}** sudah spawn! Klik tombol di bawah jika sudah mati.", view=view)
            to_remove.append(boss)
    
    for boss in to_remove: del data[boss]
    if to_remove: simpan_data(data)

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
        pesan += f"**{nama.capitalize()}**\n  > 🇮🇩 {waktu_wib} WIB | 🇵🇭 {waktu_pht} PHT\n  > ⏳ {sisa}m lagi\n"
    await ctx.send(pesan)

@bot.event
async def on_ready():
    monitor_boss.start()
    print(f'✅ Bot Ready: {bot.user}')

bot.run(TOKEN)
