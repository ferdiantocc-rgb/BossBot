import discord
from discord.ext import commands, tasks
import requests
import os
import pytz
from datetime import datetime, timedelta

# --- KONFIGURASI ---
SHEET_URL = os.environ.get('SHEET_URL')
TOKEN = os.environ.get('TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- FUNGSI FORMAT WAKTU ---
def clean_row(val):
    """Membersihkan data agar menjadi format 24 jam HH:MM"""
    if not val or val == "" or val == "-": return None
    val = str(val).strip()
    try:
        # Jika format mengandung AM/PM, konversi ke 24 jam
        if "AM" in val.upper() or "PM" in val.upper():
            return datetime.strptime(val, "%I:%M:%S %p").strftime("%H:%M")
        # Jika format sudah HH:MM:SS, ambil HH:MM
        elif ":" in val:
            return ":".join(val.split(':')[:2])
    except:
        return None
    return val

def get_pht(wib_time_str):
    """Kalkulasi WIB ke PHT (WIB + 1 jam)"""
    try:
        h, m = map(int, wib_time_str.split(':'))
        h = (h + 1) % 24
        return f"{h:02d}:{m:02d}"
    except: 
        return "--:--"

# --- KOMPONEN UI ---
class BossView(discord.ui.View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name

    @discord.ui.button(label="Boss Mati (Mulai Ulang) ✅", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"✅ {self.boss_name} tercatat mati.", ephemeral=False)

# --- TASK LOOP (NOTIFIKASI -10, -5, 0) ---
@tasks.loop(minutes=1)
async def check_boss_timer():
    if not CHANNEL_ID or not SHEET_URL: return
    try:
        res = requests.get(SHEET_URL).json()
        now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
        channel = bot.get_channel(CHANNEL_ID)
        
        for row in res.get('interval', [])[1:]:
            if not row[0]: continue
            spawn_str = clean_row(row[3])
            if not spawn_str: continue
            
            h, m = map(int, spawn_str.split(':'))
            respawn_dt = now_wib.replace(hour=h, minute=m, second=0, microsecond=0)
            
            diff = (respawn_dt - now_wib).total_seconds() / 60
            
            if 9.5 <= diff <= 10.5:
                await channel.send(f"@everyone ⚠️ **10 Minutes Left!** {row[0]} will spawn soon.")
            elif 4.5 <= diff <= 5.5:
                await channel.send(f"@everyone ⏳ **5 Minutes Left!** Prepare for {row[0]}!")
            elif -0.5 <= diff <= 0.5:
                pht_time = get_pht(spawn_str)
                dual_time = f"🇮🇩 {spawn_str} WIB | 🇵🇭 {pht_time} PHT"
                await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**\n⏰ {dual_time}", view=BossView(row[0]))
    except Exception as e:
        print(f"Error loop: {e}")

# --- COMMANDS ---
@bot.command()
async def status(ctx):
    res = requests.get(SHEET_URL).json()
    embed = discord.Embed(title="⚔️ JADWAL RESPAWN", color=discord.Color.gold())
    for row in res.get('interval', [])[1:]:
        if row[0]:
            wib = clean_row(row[3])
            # Tampilkan waktu PH selama data WIB ditemukan
            pht_val = get_pht(wib) if wib else "--:--"
            embed.add_field(name=f"{row[0]}", value=f"🇮🇩 {wib if wib else '--:--'} WIB | 🇵🇭 {pht_val} PHT", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def list_fix(ctx):
    res = requests.get(SHEET_URL).json()
    msg = "```fix\n"
    msg += f"{'HARI':<12} | {'JAM':<11} | {'BOSS'}\n"
    msg += "-"*40 + "\n"
    for row in res.get('fix', [])[1:]:
        if len(row) >= 3:
            msg += f"{row[0]:<12} | {row[1]:<11} | {row[2]}\n"
    msg += "```"
    await ctx.send(f"📅 **JADWAL BOSS TETAP 🇮🇩🇵🇭**\n{msg}")

@bot.event
async def on_ready():
    check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
