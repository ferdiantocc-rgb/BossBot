import discord
from discord.ext import commands
import requests
import os

TOKEN = 'MASUKKAN_TOKEN_BOT_ANDA'
WEBHOOK_URL = 'MASUKKAN_URL_GOOGLE_SCRIPT_ANDA'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class BossView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ego Mati", style=discord.ButtonStyle.danger)
    async def ego_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        requests.post(WEBHOOK_URL, json={"bossName": "Ego"})
        await interaction.response.send_message("Waktu mati Ego sudah dicatat!", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Bot sudah online!')

@bot.command()
async def menu(ctx):
    await ctx.send("Klik tombol di bawah saat bos mati:", view=BossView())

bot.run(TOKEN)