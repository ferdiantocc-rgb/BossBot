import discord
from discord.ext import commands
from discord.ui import Button, View
import requests
import os
import pytz
from datetime import datetime, timedelta

TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

WIB = pytz.timezone('Asia/Jakarta')
PHT = pytz.timezone('Asia/Manila')

class BossView(View):
    def __init__(self, boss_name):
        super().__init__(timeout=None)
        self.boss_name = boss_name

    @discord.ui.button(label="💀 Boss Sudah Mati", style=discord.ButtonStyle.danger)
    async def confirm_death(self, interaction: discord.Interaction, button: discord.ui.Button):
        now_wib = datetime.now(WIB)
        requests.post(SHEET_URL, json={"bossName": self.boss_name, "deathTime": now_wib.strftime("%H:%M:%S")})
        
        await interaction.response.send_message(f"✅ **{self.boss_name}** tercatat mati di {now_wib.strftime('%H:%M')} WIB.")

@bot.command()
async def boss(ctx, *, boss_name):
    await ctx.send(f"Klik tombol jika **{boss_name}** dikalahkan:", view=BossView(boss_name))

@bot.command()
async def status(ctx):
    response = requests.get(SHEET_URL).json()
    data = response['interval']
    
    msg = "**📊 Status Boss (Interval):**\n"
    for row in data[1:]: # Skip header
        name, interval, death_time, respawn_time = row[0], row[1], row[2], row[3]
        if death_time:
            msg += f"• **{name}**: Mati {death_time} | Respawn ± {respawn_time}\n"
        else:
            msg += f"• **{name}**: Belum ada data kematian.\n"
    await ctx.send(msg)

@bot.command()
async def list_fix(ctx):
    data = requests.get(SHEET_URL).json()['fix']
    msg = "**📅 Jadwal Boss Tetap:**\n"
    for row in data[1:]:
        msg += f"• **{row[2]}** | 🕒 {row[1]} | 📅 {row[0]}\n"
    await ctx.send(msg)

@bot.event
async def on_ready():
    print(f'Bot siap! Data sinkronisasi: {SHEET_URL}')

bot.run(TOKEN)
