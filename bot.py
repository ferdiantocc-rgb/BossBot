import discord
from discord.ext import commands
import os
import requests

# Mengambil Token dan URL dari Railway Variables (Brankas Aman)
TOKEN = os.environ.get('TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot sudah online!')

@bot.command()
async def menu(ctx):
    await ctx.send("Bot pengingat boss sedang berjalan!")

# Fungsi untuk kirim data ke Google Script
def kirim_ke_google(data):
    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json={"data": data})
        except Exception as e:
            print(f"Gagal mengirim ke Google: {e}")

bot.run(TOKEN)
