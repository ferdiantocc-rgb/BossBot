import discord, requests, os, pytz, time
from discord.ext import commands, tasks
from datetime import datetime, timedelta

TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
WIB = pytz.timezone('Asia/Jakarta')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@tasks.loop(minutes=1)
async def check_boss_timer():
    try:
        r = requests.get(f"{SHEET_URL}&t={time.time()}", timeout=15)
        data = r.json()
        now = datetime.now(WIB)
        ch = bot.get_channel(CHANNEL_ID)
        if not ch: return
        
        for row in data.get('interval', [])[1:]:
            if not row[0] or not row[2]: continue
            # Gabungkan tanggal hari ini dengan jam dari kolom C
            jam_mati_str = str(row[2]).strip()
            waktu_mati = datetime.strptime(jam_mati_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=WIB)
            
            # Jika jam mati lebih besar dari sekarang, anggap kemarin
            if waktu_mati > now: waktu_mati -= timedelta(days=1)
            
            spawn = waktu_mati + timedelta(minutes=int(row[1]))
            diff = (spawn - now).total_seconds() / 60
            
            if -0.5 <= diff <= 0.5: await ch.send(f"@everyone ⚔️ {row[0]} SPAWNED!")
            elif 4.5 <= diff <= 5.5: await ch.send(f"@everyone ⏳ 5m left: {row[0]}")
            elif 9.5 <= diff <= 10.5: await ch.send(f"@everyone 📢 10m left: {row[0]}")
    except Exception as e: print(f"Error: {e}")

@bot.command()
async def status(ctx):
    try:
        r = requests.get(f"{SHEET_URL}&t={time.time()}").json()
        now = datetime.now(WIB)
        embed = discord.Embed(title="JADWAL BOSS", color=discord.Color.gold())
        for row in r.get('interval', [])[1:]:
            if row[0] and row[2]:
                waktu_mati = datetime.strptime(str(row[2]).strip(), "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=WIB)
                if waktu_mati > now: waktu_mati -= timedelta(days=1)
                spawn = waktu_mati + timedelta(minutes=int(row[1]))
                diff = int((spawn - now).total_seconds())
                t = f"{diff//3600}j {diff%3600//60}m lagi" if diff > 0 else "🔴 Spawn/Mati"
                embed.add_field(name=row[0], value=f"Next: {spawn.strftime('%H:%M')} WIB\n{t}", inline=False)
        await ctx.send(embed=embed)
    except: await ctx.send("Gagal memuat status.")

bot.run(TOKEN)
