import discord
from discord.ext import commands
from discord.ui import Button, View
import requests
import os
import pytz
from datetime import datetime

# Mengambil data dari Variables yang Anda set di Railway
TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Tombol Interaktif ---
class BossView(View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name

    @discord.ui.button(label="💀 Boss Sudah Mati", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
        death_time_str = now_wib.strftime("%H:%M:%S")
        
        # Kirim data ke Apps Script
        try:
            requests.post(SHEET_URL, json={"bossName": self.boss_name, "deathTime": death_time_str})
            await interaction.response.send_message(f"✅ **{self.boss_name}** tercatat mati di {now_wib.strftime('%H:%M')} WIB.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Gagal update data: {e}")

# --- Command Bot ---
@bot.command()
async def boss(ctx, *, boss_name):
    """Gunakan !boss [nama] untuk memunculkan tombol"""
    await ctx.send(f"Klik tombol jika **{boss_name}** dikalahkan:", view=BossView(boss_name))

@bot.command()
async def status(ctx):
    """Mengecek status boss interval"""
    try:
        response = requests.get(SHEET_URL).json()
        data = response['interval']
        msg = "**📊 Status Boss (Interval):**\n"
        for row in data[1:]: # Skip header
            if row[0]: # Nama boss
                msg += f"• **{row[0]}** | Mati: {row[2]} | Respawn: {row[3]}\n"
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"Error mengambil status: {e}")

@bot.command()
async def list_fix(ctx):
    """Mengecek jadwal boss tetap"""
    try:
        response = requests.get(SHEET_URL).json()
        data = response['fix']
        msg = "**📅 Jadwal Boss Tetap:**\n"
        for row in data[1:]:
            if row[2]: # Nama boss
                msg += f"• {row[2]} | 🕒 {row[1]} | 📅 {row[0]}\n"
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"Error mengambil jadwal: {e}")

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} sudah online dan siap!')

# Jalankan bot
bot.run(TOKEN)
