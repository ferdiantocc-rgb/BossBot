import discord, requests, os, pytz, time
from discord.ext import commands, tasks
from datetime import datetime

TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
WIB = pytz.timezone('Asia/Jakarta')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

class BossView(discord.ui.View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name
    @discord.ui.button(label="Boss Mati ✅", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_wib = datetime.now(WIB).strftime('%H:%M')
        requests.post(SHEET_URL, json={"bossName": self.boss_name, "newTime": now_wib, "user": interaction.user.name})
        await interaction.response.send_message(f"✅ {self.boss_name} mati oleh {interaction.user.name}.", ephemeral=True)

@tasks.loop(minutes=1)
async def check_boss_timer():
    try:
        res = requests.get(f"{SHEET_URL}?t={time.time()}", timeout=15).json()
        now = datetime.now(WIB)
        channel = bot.get_channel(CHANNEL_ID)
        hari = now.strftime('%A').lower()

        # Notifikasi Interval
        for row in res.get('interval', [])[1:]:
            if not row[0] or not row[4] or "T" in str(row[4]): continue
            spawn_dt = datetime.strptime(str(row[4]), "%d/%m/%Y %H:%M").replace(tzinfo=WIB)
            diff = (spawn_dt - now).total_seconds() / 60
            if -0.5 <= diff <= 0.5: await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**", view=BossView(row[0]))
            elif 4.5 <= diff <= 5.5: await channel.send(f"⚠️ **5m left** for {row[0]}!")
            elif 9.5 <= diff <= 10.5: await channel.send(f"⚠️ **10m left** for {row[0]}!")

        # Notifikasi Fix
        for row in res.get('fix', [])[4:]:
            if row[0] and hari in row[0].lower():
                try:
                    fix_dt = datetime.strptime(row[1].split('/')[0].strip(), "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=WIB)
                    diff = (fix_dt - now).total_seconds() / 60
                    if -0.5 <= diff <= 0.5: await channel.send(f"@everyone ⚔️ **{row[2]} (Fix) SPAWNED!**")
                    elif 4.5 <= diff <= 5.5: await channel.send(f"⚠️ **5m left** for {row[2]} (Fix)!")
                    elif 9.5 <= diff <= 10.5: await channel.send(f"⚠️ **10m left** for {row[2]} (Fix)!")
                except: continue
    except Exception as e: print(f"Loop Error: {e}")

@bot.command()
async def status(ctx):
    try:
        res = requests.get(f"{SHEET_URL}?t={time.time()}").json()
        embed = discord.Embed(title="⚔️ JADWAL BOSS", color=discord.Color.gold())
        for row in res.get('interval', [])[1:]:
            if row[0] and row[4] and "T" not in str(row[4]):
                killer = f" | 💀 {row[5]}" if len(row) > 5 and row[5] else ""
                embed.add_field(name=row[0], value=f"📅 {row[4]} WIB{killer}", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat status.")

@bot.command()
async def fix(ctx):
    try:
        res = requests.get(f"{SHEET_URL}?t={time.time()}").json()
        embed = discord.Embed(title="⚔️ JADWAL BOSS FIX", color=discord.Color.red())
        for row in res.get('fix', [])[4:]:
            if row[0]: embed.add_field(name=f"{row[2]}", value=f"📅 {row[1]} WIB", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat jadwal Fix.")

@bot.event
async def on_ready():
    check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
