import discord, requests, os, pytz, time
from discord.ext import commands, tasks
from datetime import datetime

TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
WIB = pytz.timezone('Asia/Jakarta')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

@tasks.loop(minutes=1)
async def check_boss_timer():
    try:
        # Menambahkan parameter waktu agar tidak membaca data lama (cache)
        res = requests.get(f"{SHEET_URL}?t={time.time()}", timeout=15).json()
        now = datetime.now(WIB)
        channel = bot.get_channel(CHANNEL_ID)
        
        # Notifikasi Interval
        for row in res.get('interval', [])[1:]:
            if not row[0] or not row[4] or "/" not in str(row[4]): continue
            try:
                spawn_dt = datetime.strptime(str(row[4]).strip(), "%d/%m/%Y %H:%M").replace(tzinfo=WIB)
                diff = (spawn_dt - now).total_seconds() / 60
                if -0.5 <= diff <= 0.5: await channel.send(f"@everyone ⚔️ **{row[0]} SPAWNED!**")
                elif 4.5 <= diff <= 5.5: await channel.send(f"⚠️ **5m left** for {row[0]}!")
            except: continue
    except Exception as e: print(f"Loop error: {e}")

@bot.command()
async def status(ctx):
    try:
        res = requests.get(f"{SHEET_URL}?t={time.time()}").json()
        embed = discord.Embed(title="⚔️ JADWAL BOSS", color=discord.Color.gold())
        for row in res.get('interval', [])[1:]:
            if row[0] and row[4] and "/" in str(row[4]):
                embed.add_field(name=row[0], value=f"📅 {row[4]} WIB", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat status.")

@bot.event
async def on_ready():
    check_boss_timer.start()
    print('Bot Ready!')

bot.run(TOKEN)
