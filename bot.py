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

# DURASI DALAM MENIT
DURASI_BOSS = {
    "venatus": 600, "viorent": 600, "ladydalia": 1080, "ego": 1260,
    "shuliar": 2100, "larba": 2100, "catena": 2100, "livera": 1440,
    "undomiel": 1440, "araneo": 1440, "wannitas": 2880, "metus": 2880,
    "duplican": 2880, "baronbraudmore": 1920, "gareth": 1920, "amentis": 1740,
    "titore": 2220, "generalaquleus": 1740, "ordo": 3720, "asta": 3720,
    "secreta": 3720, "supore": 3720
}

# --- SETUP ---
creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

notifikasi_sent = {}
notifikasi_fix = {} # Pelacak untuk fix boss

def simpan_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

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
        menit_durasi = DURASI_BOSS.get(self.nama_boss.lower(), 60)
        data = muat_data()
        data[self.nama_boss.lower()] = (datetime.now(WIB) + timedelta(minutes=menit_durasi)).isoformat()
        simpan_data(data)
        await interaction.response.send_message(f"✅ {self.nama_boss.capitalize()} di-reset ({menit_durasi} menit lagi).")
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
        
        if sisa == 10 and not notifikasi_sent[boss]["10"]:
            if channel: await channel.send("@everyone ⚠️ Boss **" + boss.capitalize() + "** spawn dalam 10 menit!", allowed_mentions=discord.AllowedMentions.all())
            notifikasi_sent[boss]["10"] = True
        elif sisa == 5 and not notifikasi_sent[boss]["5"]:
            if channel: await channel.send("@everyone ⚠️ Boss **" + boss.capitalize() + "** spawn dalam 5 menit!", allowed_mentions=discord.AllowedMentions.all())
            notifikasi_sent[boss]["5"] = True
        elif sisa <= 0:
            view = BossDoneView(boss)
            if channel: await channel.send(f"⚔️ Boss **{boss.capitalize()}** sudah spawn! Klik jika sudah mati.", view=view)
            to_remove.append(boss)
            if boss in notifikasi_sent: del notifikasi_sent[boss]
            
    for boss in to_remove: del data[boss]
    if to_remove: simpan_data(data)

@tasks.loop(minutes=1)
async def monitor_fix_boss():
    now = datetime.now(WIB)
    current_day = now.strftime("%A")
    channel = bot.get_channel(CHANNEL_ID)
    try:
        data = client.open("Master Boss timer").worksheet("fix").get_values("A4:C35")
        for row in data:
            if len(row) >= 3 and current_day.lower() in row[0].lower():
                jam_fix = datetime.strptime(row[1].split('/')[0].strip(), "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=WIB)
                sisa = int((jam_fix - now).total_seconds() / 60)
                
                boss_key = f"{row[2]}_{row[1]}" # ID unik untuk fix boss
                if boss_key not in notifikasi_fix: notifikasi_fix[boss_key] = {"10": False, "5": False}
                
                if sisa == 10 and not notifikasi_fix[boss_key]["10"]:
                    if channel: await channel.send(f"@everyone ⚠️ Fix Boss **{row[2]}** spawn dalam 10 menit!", allowed_mentions=discord.AllowedMentions.all())
                    notifikasi_fix[boss_key]["10"] = True
                elif sisa == 5 and not notifikasi_fix[boss_key]["5"]:
                    if channel: await channel.send(f"@everyone ⚠️ Fix Boss **{row[2]}** spawn dalam 5 menit!", allowed_mentions=discord.AllowedMentions.all())
                    notifikasi_fix[boss_key]["5"] = True
                elif sisa == 0:
                    if channel: await channel.send(f"@everyone 📢 **FIX BOSS ALERT!** Sekarang spawn: **{row[2]}**", allowed_mentions=discord.AllowedMentions.all())
    except Exception as e: print(f"Error monitor_fix_boss: {e}")

# --- COMMANDS ---
@bot.command()
async def startboss(ctx, nama: str, menit: int):
    data = muat_data()
    data[nama.lower()] = (datetime.now(WIB) + timedelta(minutes=menit)).isoformat()
    simpan_data(data)
    await ctx.send(f"✅ Pengingat **{nama.capitalize()}** disetel ({menit} menit lagi).")

@bot.command()
async def status(ctx):
    data = muat_data()
    if not data: await ctx.send("✅ Tidak ada boss yang dipantau.")
    else:
        now = datetime.now(WIB).replace(tzinfo=None)
        pesan = "⚔️ **JADWAL BOSS**\n"
        for nama, waktu_str in data.items():
            spawn = datetime.fromisoformat(waktu_str).replace(tzinfo=None)
            waktu_wib = spawn.strftime("%H:%M")
            waktu_pht = (spawn + timedelta(hours=1)).strftime("%H:%M")
            diff = spawn - now
            days, rem = divmod(int(diff.total_seconds() / 60), 1440)
            hours, minutes = divmod(rem, 60)
            cd = f"{days}h {hours}j {minutes}m" if days > 0 else f"{hours}j {minutes}m"
            pesan += f"**{nama.capitalize()}**\n  > 🇮🇩 {waktu_wib} WIB | 🇵🇭 {waktu_pht} PHT\n  > ⏳ {cd} lagi\n"
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
                jam_wib = row[1].split('/')[0].strip()
                jam_pht = (datetime.strptime(jam_wib, "%H:%M") + timedelta(hours=1)).strftime("%H:%M")
                pesan += f"• **{row[2]}**\n  └ 🇮🇩 {jam_wib} WIB | 🇵🇭 {jam_pht} PHT\n"
                found = True
        await ctx.send(pesan if found else "Tidak ada jadwal fix hari ini.")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.event
async def on_ready():
    monitor_boss.start()
    monitor_fix_boss.start()
    print(f'✅ Bot Ready: {bot.user}')

bot.run(TOKEN)
