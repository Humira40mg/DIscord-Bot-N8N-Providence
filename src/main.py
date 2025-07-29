import discord
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
print(TOKEN)
N8N_PUBLIC_ENDPOINT = 'http://localhost:5678/webhook/everyone' 

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

lock = asyncio.Lock()

@client.event
async def on_ready():
    print(f'Connecté en tant que {client.user}!')

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if client.user in message.mentions:
        async with lock:
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {'message': message.content, 'id': str(message.author.id) + str(datetime.now().timestamp())}
                    async with session.post(N8N_PUBLIC_ENDPOINT, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            await message.reply(f"{data.get('response', 'ok')}".split("</think>")[1])
                        else:
                            await message.reply(f"Désolé j'ai rencontré une erreur sur mon chemain. {resp.status}")
            except Exception as e:
                await message.reply(f"Erreur : {e}")

client.run(TOKEN)
