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

# --- FUNGSI UTAMA ---
def get_pht(wib_time_str):
    """Mengonversi jam HH:MM WIB ke PHT (+1 jam)"""
    try:
        h, m = map(int, wib_time_str.split(':'))
        wib = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        pht = wib + timedelta(hours=1)
        return pht.strftime('%H:%M')
    except:
        return "--:--"

def clean_row(val):
    """Membersihkan nilai sel agar menjadi string HH:MM"""
    if not val: return None
    # Jika objek datetime dari sheet, ambil jamnya
    if hasattr(val, 'strftime'): return val.strftime('%H:%M')
    # Jika string panjang, coba potong
    if isinstance(val, str) and ":" in val:
        parts = val.split(':')
        return f"{parts[0][-2:]}:{parts[1][:2]}"
    return str(val)

# --- TOMBOL ---
class BossView(discord.ui.View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name

    @discord.ui.button(label="Boss Mati (Mulai Ulang) ✅", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"✅ {self.boss_name} tercatat mati. Jadwal diperbarui.", ephemeral=False)

# --- TASK LOOP (NOTIFIKASI) ---
@tasks.loop(minutes=1)
async def check_boss_timer():
    if not CHANNEL_ID or not SHEET_URL: return
    try:
        res = requests.get(SHEET_URL).json()
        data = res.get('interval', [])
        now = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%H:%M')
        channel = bot.get_channel(CHANNEL_ID)
        
        for row in data[1:]:
            if not row[0]: continue
            spawn_wib = clean_row(row[3])
            
            if spawn_wib == now:
                await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**\n🇮🇩 {spawn_wib} WIB | 🇵🇭 {get_pht(spawn_wib)} PHT", view=BossView(row[0]))
    except: pass

# --- COMMANDS ---
@bot.command()
async def status(ctx):
    res = requests.get(SHEET_URL).json()
    embed = discord.Embed(title="⚔️ JADWAL RESPAWN", color=discord.Color.gold())
    for row in res.get('interval', [])[1:]:
        if row[0]:
            wib = clean_row(row[3])
            embed.add_field(name=f" {row[0]}", value=f"🇮🇩 {wib} WIB | 🇵🇭 {get_pht(wib)} PHT", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def list_fix(ctx):
    res = requests.get(SHEET_URL).json()
    msg = "**📅 JADWAL BOSS TETAP**\n"
    for row in res.get('fix', [])[1:]:
        if len(row) >= 3:
            msg += f"• {row[0]} | 🕒 {row[1]} | ⚔️ {row[2]}\n"
    await ctx.send(msg)

@bot.event
async def on_ready():
    check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
