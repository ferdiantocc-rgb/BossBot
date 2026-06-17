import discord
from discord.ext import commands, tasks
import requests
import os
import pytz
from datetime import datetime, timedelta

# --- SETUP VARIABEL DARI RAILWAY ---
SHEET_URL = os.environ.get('SHEET_URL')
TOKEN = os.environ.get('TOKEN')
# Gunakan default 0 jika CHANNEL_ID gagal dimuat, pastikan diisi di Railway!
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0)) 

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- FUNGSI BANTUAN ---
def clean_time(val):
    """Mengambil format HH:MM dari data spreadsheet"""
    if not val: return "-"
    if isinstance(val, str) and "T" in val:
        try: return val.split("T")[1][:5]
        except: return val
    return str(val)

def get_dual_time_str(time_str):
    """Mengubah format HH:MM menjadi dua zona waktu (WIB & PHT)"""
    try:
        wib_tz = pytz.timezone('Asia/Jakarta')
        pht_tz = pytz.timezone('Asia/Manila')
        now = datetime.now(wib_tz)
        
        h, m = map(int, time_str.split(':'))
        dt_wib = now.replace(hour=h, minute=m, second=0, microsecond=0)
        dt_pht = dt_wib.astimezone(pht_tz)
        
        return f"🇮🇩 **ID:** {dt_wib.strftime('%H:%M')} WIB | 🇵🇭 **PH:** {dt_pht.strftime('%H:%M')} PHT"
    except:
        return time_str

# --- TOMBOL INTERAKTIF ---
class BossView(discord.ui.View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name

    @discord.ui.button(label="Boss Mati (Mulai Ulang) ✅", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
        now_pht = now_wib.astimezone(pytz.timezone('Asia/Manila'))
        death_time_wib = now_wib.strftime('%H:%M')
        death_time_pht = now_pht.strftime('%H:%M')
        
        # Kirim data ke Apps Script (Opsional jika Anda sudah setup post di Apps Script)
        try:
            requests.post(SHEET_URL, json={"bossName": self.boss_name, "deathTime": death_time_wib})
        except:
            pass # Lanjut ke pesan sukses meskipun gagal update sheet
            
        await interaction.response.send_message(
            f"📢 **{self.boss_name}** defeated! Respawn timer restarted.\n⏰ 🇮🇩 **ID:** {death_time_wib} WIB | 🇵🇭 **PH:** {death_time_pht} PHT", 
            ephemeral=False
        )
        # Mematikan tombol setelah diklik
        button.disabled = True
        await interaction.message.edit(view=self)

# --- LOOP NOTIFIKASI OTOMATIS ---
@tasks.loop(minutes=1)
async def check_boss_timer():
    if CHANNEL_ID == 0: 
        print("CHANNEL_ID belum diatur!")
        return
        
    try:
        response = requests.get(SHEET_URL).json()
        data = response['interval']
        now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
        channel = bot.get_channel(CHANNEL_ID)
        
        for row in data[1:]:
            boss_name = row[0]
            respawn_raw = row[3]
            
            if boss_name and respawn_raw:
                time_str = clean_time(respawn_raw)
                if time_str == "-": continue
                
                # Hitung waktu respawn
                try:
                    h, m = map(int, time_str.split(':'))
                    respawn_dt = now_wib.replace(hour=h, minute=m, second=0, microsecond=0)
                    
                    # Jika waktu respawn sudah lewat hari ini, anggap besok
                    if respawn_dt < now_wib and (now_wib - respawn_dt).total_seconds() > 3600:
                        respawn_dt += timedelta(days=1)
                        
                    diff = (respawn_dt - now_wib).total_seconds() / 60
                    
                    dual_time = get_dual_time_str(time_str)
                    
                    # Notifikasi -10 Menit
                    if 9.5 <= diff <= 10.5:
                        await channel.send(f"⚠️ **10 MINUTES LEFT!** Prepare for **{boss_name}**! @everyone\n⏰ {dual_time}")
                    # Notifikasi -5 Menit
                    elif 4.5 <= diff <= 5.5:
                        await channel.send(f"⏳ **5 MINUTES LEFT!** Get ready for **{boss_name}**! @everyone\n⏰ {dual_time}")
                    # Notifikasi Boss Spawn (0 Menit) + Tombol
                    elif -0.5 <= diff <= 0.5:
                        await channel.send(
                            f"⚔️ **BOSS SPAWNED!** Attack **{boss_name}** now! @everyone\n⏰ {dual_time}",
                            view=BossView(boss_name)
                        )
                except Exception as e:
                    print(f"Error hitung waktu {boss_name}: {e}")
                    continue
    except Exception as e:
        print(f"Error loop utama: {e}")

# --- COMMAND BOT ---
@bot.command()
async def status(ctx):
    """Command untuk melihat jadwal lengkap rapi"""
    if not SHEET_URL:
        await ctx.send("⚠️ Error: SHEET_URL belum diatur.")
        return
        
    try:
        response = requests.get(SHEET_URL).json()
        embed = discord.Embed(title="⚔️ JADWAL RESPAWN | RESPAWN SCHEDULE", color=discord.Color.dark_theme())
        
        for row in response['interval'][1:]:
            boss_name = row[0]
            respawn_raw = row[3]
            if boss_name:
                respawn_time = clean_time(respawn_raw)
                if respawn_time != "-":
                    times = get_dual_time_str(respawn_time)
                    embed.add_field(name=f"⚔️ {boss_name}", value=f"Spawn: {times}", inline=False)
                    
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error mengambil status: {e}")

@bot.event
async def on_ready():
    check_boss_timer.start()
    print(f'Bot {bot.user.name} online dan siap mengirim notifikasi!')

bot.run(TOKEN)
