import discord
from discord.ext import commands, tasks
import requests, os, pytz
from datetime import datetime, timedelta

TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_pht(wib_str):
    try:
        h, m = map(int, wib_str.split(':'))
        return f"{(h + 1) % 24:02d}:{m:02d}"
    except: return "--:--"

class BossView(discord.ui.View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name
    @discord.ui.button(label="Boss Mati ✅", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_wib = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%H:%M')
        requests.post(SHEET_URL, json={"bossName": self.boss_name, "newTime": now_wib})
        await interaction.response.send_message(f"✅ {self.boss_name} tercatat mati.", ephemeral=True)

@tasks.loop(minutes=1)
async def check_boss_timer():
    try:
        res = requests.get(SHEET_URL).json()
        now = datetime.now(pytz.timezone('Asia/Jakarta'))
        channel = bot.get_channel(CHANNEL_ID)
        
        # 1. Cek Interval Boss (Kolom E: index 4)
        for row in res.get('interval', [])[1:]:
            if not row[0] or not row[4]: continue
            spawn_dt = datetime.strptime(row[4], "%d/%m/%Y %H:%M").replace(tzinfo=pytz.timezone('Asia/Jakarta'))
            diff = (spawn_dt - now).total_seconds() / 60
            
            if -0.5 <= diff <= 0.5:
                await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**", view=BossView(row[0]))
            elif 4.5 <= diff <= 5.5:
                await channel.send(f"⚠️ **5 Minutes left** for {row[0]}!")
            elif 9.5 <= diff <= 10.5:
                await channel.send(f"⚠️ **10 Minutes left** for {row[0]}!")

        # 2. Cek Fix Boss (Logika lama, disesuaikan)
        hari_ini = now.strftime('%A').lower()
        for row in res.get('fix', [])[1:]:
            if hari_ini in row[0].lower():
                fix_time = datetime.strptime(row[1], "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=pytz.timezone('Asia/Jakarta'))
                diff = (fix_time - now).total_seconds() / 60
                if -0.5 <= diff <= 0.5: await channel.send(f"@everyone ⚔️ **{row[2]} (Fix) SPAWNED!**")
                elif 4.5 <= diff <= 5.5: await channel.send(f"⚠️ **5 Minutes left** for {row[2]} (Fix)!")
                elif 9.5 <= diff <= 10.5: await channel.send(f"⚠️ **10 Minutes left** for {row[2]} (Fix)!")
    except Exception as e: print(f"Loop Error: {e}")

@bot.command()
async def status(ctx):
    res = requests.get(SHEET_URL).json()
    embed = discord.Embed(title="⚔️ JADWAL BOSS", color=discord.Color.gold())
    for row in res.get('interval', [])[1:]:
        if row[0]:
            wib = row[3] # Kolom D (Jam Respawn)
            embed.add_field(name=row[0], value=f"🇮🇩 {wib} WIB | 🇵🇭 {get_pht(wib)} PHT", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
