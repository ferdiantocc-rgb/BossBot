import discord, requests, os, pytz, time
from discord.ext import commands, tasks
from datetime import datetime

TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
WIB = pytz.timezone('Asia/Jakarta')

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
        now_wib = datetime.now(WIB).strftime('%H:%M')
        # Kirim update ke Google Apps Script
        requests.post(SHEET_URL, json={"bossName": self.boss_name, "newTime": now_wib})
        await interaction.response.send_message(f"✅ {self.boss_name} tercatat mati.", ephemeral=True)

@tasks.loop(minutes=1)
async def check_boss_timer():
    try:
        # Menambahkan parameter &t=time.time() untuk membuang cache
        res = requests.get(f"{SHEET_URL}&t={time.time()}", timeout=15).json()
        now = datetime.now(WIB)
        channel = bot.get_channel(CHANNEL_ID)
        if not channel: return
        hari = now.strftime('%A').lower()

        # 1. Cek Interval Boss
        for row in res.get('interval', [])[1:]:
            if not row[0] or not row[4] or "#" in str(row[4]): continue
            try:
                spawn_dt = datetime.strptime(row[4], "%d/%m/%Y %H:%M").replace(tzinfo=WIB)
                diff = (spawn_dt - now).total_seconds() / 60
                
                if -0.5 <= diff <= 0.5: 
                    await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**", view=BossView(row[0]))
                elif 4.5 <= diff <= 5.5: 
                    await channel.send(f"@everyone ⚠️ **5 Minutes left** for {row[0]}!")
                elif 9.5 <= diff <= 10.5: 
                    await channel.send(f"@everyone 📢 **10 Minutes left** for {row[0]}!")
            except: continue

        # 2. Cek Fix Boss
        for row in res.get('fix', [])[4:]:
            if row[0] and hari in row[0].lower():
                try:
                    waktu_mulai = row[1].split('/')[0].strip()
                    fix_dt = datetime.strptime(waktu_mulai, "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=WIB)
                    diff = (fix_dt - now).total_seconds() / 60
                    if -0.5 <= diff <= 0.5: await channel.send(f"@everyone ⚔️ **{row[2]} (Fix) SPAWNED!**")
                    elif 4.5 <= diff <= 5.5: await channel.send(f"@everyone ⚠️ **5 Minutes left** for {row[2]} (Fix)!")
                    elif 9.5 <= diff <= 10.5: await channel.send(f"@everyone 📢 **10 Minutes left** for {row[2]} (Fix)!")
                except: continue
    except Exception as e: print(f"Loop Error: {e}")

@bot.command()
async def status(ctx):
    try:
        res = requests.get(f"{SHEET_URL}&t={time.time()}", timeout=10).json()
        now = datetime.now(WIB)
        embed = discord.Embed(title="⚔️ JADWAL BOSS", color=discord.Color.gold())
        for row in res.get('interval', [])[1:]:
            if row[0] and row[4] and "#" not in str(row[4]):
                spawn_dt = datetime.strptime(row[4], "%d/%m/%Y %H:%M").replace(tzinfo=WIB)
                diff = int((spawn_dt - now).total_seconds())
                countdown = "🔴 Spawn/Mati" if diff < 0 else f"⏳ {diff // 3600}j {(diff % 3600) // 60}m lagi"
                embed.add_field(name=row[0], value=f"🇮🇩 {row[3]} WIB | 🇵🇭 {get_pht(row[3])} PHT\n{countdown}", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat status. Pastikan akses Web App sudah 'Anyone'.")

@bot.event
async def on_ready():
    if not check_boss_timer.is_running(): check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
