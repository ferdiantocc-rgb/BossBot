import discord, requests, os, pytz
from discord.ext import commands, tasks
from datetime import datetime

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
        res = requests.get(SHEET_URL, timeout=15).json()
        now = datetime.now(pytz.timezone('Asia/Jakarta'))
        channel = bot.get_channel(CHANNEL_ID)
        
        # 1. Cek Interval Boss
        for row in res.get('interval', [])[1:]:
            if not row[0] or not row[4] or "#" in str(row[4]): continue
            try:
                spawn_dt = datetime.strptime(row[4], "%d/%m/%Y %H:%M").replace(tzinfo=pytz.timezone('Asia/Jakarta'))
                diff = (spawn_dt - now).total_seconds() / 60
                if -0.5 <= diff <= 0.5: await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**", view=BossView(row[0]))
            except: continue

        # 2. Cek Boss Fix (Mulai dari baris ke-5 / indeks 4)
        hari = now.strftime('%A').lower()
        for row in res.get('fix', [])[4:]: 
            if row[0] and hari in row[0].lower():
                try:
                    # Ambil bagian awal waktu (contoh: 10:30 dari 10:30 / 11:30)
                    waktu_mulai = row[1].split('/')[0].strip()
                    fix_dt = datetime.strptime(waktu_mulai, "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=pytz.timezone('Asia/Jakarta'))
                    diff = (fix_dt - now).total_seconds() / 60
                    if -0.5 <= diff <= 0.5: await channel.send(f"@everyone ⚔️ **{row[2]} (Fix) SPAWNED!**")
                except: continue
    except Exception as e: print(f"Loop Error: {e}")

@bot.command()
async def status(ctx):
    try:
        res = requests.get(SHEET_URL).json()
        now = datetime.now(pytz.timezone('Asia/Jakarta'))
        embed = discord.Embed(title="⚔️ JADWAL BOSS", color=discord.Color.gold())
        for row in res.get('interval', [])[1:]:
            if row[0] and row[4] and "#" not in str(row[4]):
                spawn_dt = datetime.strptime(row[4], "%d/%m/%Y %H:%M").replace(tzinfo=pytz.timezone('Asia/Jakarta'))
                diff = int((spawn_dt - now).total_seconds())
                countdown = "🔴 Spawn/Mati" if diff < 0 else f"⏳ {diff // 3600}j {(diff % 3600) // 60}m lagi"
                embed.add_field(name=row[0], value=f"{row[3]} WIB | {countdown}", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat status.")

@bot.command()
async def fix(ctx):
    try:
        res = requests.get(SHEET_URL).json()
        now = datetime.now(pytz.timezone('Asia/Jakarta'))
        hari = now.strftime('%A').lower()
        embed = discord.Embed(title="⚔️ JADWAL BOSS FIX HARI INI", color=discord.Color.red())
        for row in res.get('fix', [])[4:]:
            if row[0] and hari in row[0].lower():
                embed.add_field(name=f"{row[2]}", value=f"Waktu: {row[1]} WIB", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat jadwal Fix.")

@bot.event
async def on_ready():
    if not check_boss_timer.is_running(): check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
