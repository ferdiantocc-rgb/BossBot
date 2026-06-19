import discord
from discord.ext import commands, tasks
import requests
import os
import pytz
from datetime import datetime

SHEET_URL = os.environ.get('SHEET_URL')
TOKEN = os.environ.get('TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def clean_row(val):
    if not val or str(val).strip() in ["", "-", "None"]: return None
    val = str(val).strip().replace('.', ':')
    if "/" in val: val = val.split('/')[0].strip()
    try:
        parts = val.split(':')
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    except: return None

def get_pht(wib_time_str):
    try:
        h, m = map(int, wib_time_str.split(':'))
        h = (h + 1) % 24
        return f"{h:02d}:{m:02d}"
    except: return "--:--"

class BossView(discord.ui.View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name
    @discord.ui.button(label="Boss Mati (Mulai Ulang) ✅", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_wib = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%H:%M')
        requests.post(SHEET_URL, json={"bossName": self.boss_name, "newTime": now_wib})
        await interaction.response.send_message(f"✅ {self.boss_name} tercatat mati.", ephemeral=False)

@tasks.loop(minutes=1)
async def check_boss_timer():
    if not CHANNEL_ID or not SHEET_URL: return
    try:
        res = requests.get(SHEET_URL).json()
        now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
        channel = bot.get_channel(CHANNEL_ID)
        
        # Cek Interval
        for row in res.get('interval', [])[1:]:
            if not row[0] or not row[3]: continue
            spawn_str = clean_row(row[3])
            if not spawn_str: continue
            h, m = map(int, spawn_str.split(':'))
            if now_wib.hour == h and now_wib.minute == m:
                await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**", view=BossView(row[0]))
            elif (h * 60 + m) - (now_wib.hour * 60 + now_wib.minute) in [10, 5]:
                await channel.send(f"@everyone ⚠️ **{ (h * 60 + m) - (now_wib.hour * 60 + now_wib.minute) } Minutes Left!** {row[0]} soon.")

        # Cek Fix Boss
        for row in res.get('fix', [])[1:]:
            if len(row) < 3: continue
            hari_ini = now_wib.strftime('%A')
            fix_str = clean_row(row[1])
            if not fix_str: continue
            h, m = map(int, fix_str.split(':'))
            if hari_ini.lower() in row[0].lower() and now_wib.hour == h and now_wib.minute == m:
                await channel.send(f"@everyone ⚔️ **{row[2]} (Fix Boss) SPAWNED!**")
            elif hari_ini.lower() in row[0].lower() and (h * 60 + m) - (now_wib.hour * 60 + now_wib.minute) in [10, 5]:
                await channel.send(f"@everyone ⏳ **{(h * 60 + m) - (now_wib.hour * 60 + now_wib.minute)} Minutes Left!** {row[2]} soon.")
    except: pass

@bot.command()
async def status(ctx):
    res = requests.get(SHEET_URL).json()
    embed = discord.Embed(title="⚔️ JADWAL RESPAWN", color=discord.Color.gold())
    for row in res.get('interval', [])[1:]:
        if row[0]:
            wib = clean_row(row[3])
            embed.add_field(name=f"{row[0]}", value=f"🇮🇩 {wib if wib else '----'} WIB | 🇵🇭 {get_pht(wib) if wib else '----'} PHT", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def list_fix(ctx):
    res = requests.get(SHEET_URL).json()
    msg = "
http://googleusercontent.com/immersive_entry_chip/0
