import discord, requests, os, pytz, time
from discord.ext import commands, tasks
from datetime import datetime, timedelta

TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
WIB = pytz.timezone('Asia/Jakarta')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class BossView(discord.ui.View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name
    @discord.ui.button(label="Boss Mati 💀", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_wib = datetime.now(WIB).strftime('%d/%m/%Y %H:%M')
        try:
            requests.post(SHEET_URL, json={"bossName": self.boss_name, "newTime": now_wib})
            await interaction.response.send_message(f"✅ {self.boss_name} dicatat mati: {now_wib} WIB.", ephemeral=False)
        except: await interaction.response.send_message("❌ Gagal update.", ephemeral=True)

@tasks.loop(minutes=1)
async def check_boss_timer():
    try:
        r = requests.get(f"{SHEET_URL}&t={time.time()}", timeout=15)
        if r.status_code != 200: return
        data = r.json()
        now = datetime.now(WIB)
        ch = bot.get_channel(CHANNEL_ID)
        if not ch: return
        
        # Cek Interval
        for row in data.get('interval', [])[1:]:
            if not row[0] or not row[1] or not row[2]: continue
            spawn = WIB.localize(datetime.strptime(row[2].strip(), "%d/%m/%Y %H:%M")) + timedelta(minutes=int(row[1]))
            diff = (spawn - now).total_seconds() / 60
            if -0.5 <= diff <= 0.5: await ch.send(f"@everyone ⚔️ {row[0]} SPAWNED!", view=BossView(row[0]))
            elif 4.5 <= diff <= 5.5: await ch.send(f"@everyone ⏳ 5m left: {row[0]}")
            elif 9.5 <= diff <= 10.5: await ch.send(f"@everyone 📢 10m left: {row[0]}")

        # Cek Fix Boss
        hari = now.strftime('%A').lower()
        for row in data.get('fix', [])[1:]:
            if not row[0] or hari not in row[0].lower(): continue
            fix_dt = datetime.strptime(row[1].strip(), "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=WIB)
            diff = (fix_dt - now).total_seconds() / 60
            if -0.5 <= diff <= 0.5: await ch.send(f"@everyone ⚔️ {row[2]} (Fix) SPAWNED!")
            elif 4.5 <= diff <= 5.5: await ch.send(f"@everyone ⏳ 5m left: {row[2]} (Fix)")
            elif 9.5 <= diff <= 10.5: await ch.send(f"@everyone 📢 10m left: {row[2]} (Fix)")
    except Exception as e: print(f"Loop Error: {e}")

@bot.command()
async def status(ctx):
    try:
        r = requests.get(f"{SHEET_URL}&t={time.time()}", timeout=10).json()
        now = datetime.now(WIB)
        embed = discord.Embed(title="JADWAL BOSS", color=discord.Color.gold())
        for row in r.get('interval', [])[1:]:
            if row[0] and row[1] and row[2]:
                spawn = WIB.localize(datetime.strptime(row[2].strip(), "%d/%m/%Y %H:%M")) + timedelta(minutes=int(row[1]))
                diff = int((spawn - now).total_seconds())
                t = f"{diff//3600}j {diff%3600//60}m lagi" if diff > 0 else "🔴 Spawn/Mati"
                embed.add_field(name=row[0], value=f"Next: {spawn.strftime('%H:%M')} WIB\n{t}", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat status.")

@bot.event
async def on_ready():
    if not check_boss_timer.is_running(): check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
