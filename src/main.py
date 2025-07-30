import discord
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
import os
import json
import time

load_dotenv()

TOKEN = os.getenv("TOKEN")
N8N_ENDPOINT = 'http://localhost:5678/webhook/jokso' 

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

lock = asyncio.Lock()
history = []
model = "gemma3:1b"

@client.event
async def on_ready():
    print(f'Connecté en tant que {client.user}!')

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == 1398833482234466456 or (message.content.startswith(".agent") and message.author.id == 254115104210026497):
        async with message.channel.typing():
            async with lock:
                try:
                    async with aiohttp.ClientSession() as session:
                        payload = {'message': message.content, 'id': str(message.author.id) + str(datetime.now().timestamp())}
                        #TODO : logger + is typing
                        async with session.post(N8N_ENDPOINT, json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                await message.reply(f"{data.get('output')}")
                            else:
                                await message.reply(f"Désolé j'ai rencontré une erreur sur mon chemain. {resp.status}")
                except Exception as e:
                    await message.reply(f"Erreur : {e}")

    elif client.user in message.mentions :
        async with lock:

            strhistory = '\n'.join(history[::-1])
            prompt = f"{message.author.mention} : {message.content}"

            payload = {
                "model": model,
                "prompt": f"{strhistory} \n{prompt}",
                "stream": True
            }
            
            reply = await message.reply("*Réflexion...*")

            buffer = []  # tokens en attente d'affichage
            full_text = ""

            # Fonction qui update le message toutes les 0.5s
            async def periodic_edit():
                nonlocal full_text
                while True:
                    if buffer:
                        full_text += ''.join(buffer)
                        buffer.clear()
                        await reply.edit(content=full_text[:2000])
                    await asyncio.sleep(0.5)  # Ajuste selon ce que Discord tolère (~0.5-1s recommandé)

            edit_task = asyncio.create_task(periodic_edit())

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"http://localhost:11434/api/generate", json=payload) as resp:
                        if resp.status != 200:
                            await reply.edit(content="Erreur lors de la génération.")
                            return

                        async for line in resp.content:
                            if not line.strip():
                                continue
                            try:
                                data = json.loads(line.decode("utf-8"))
                                token = data.get("response", "")
                                buffer.append(token)  # On ajoute au buffer
                            except Exception as e:
                                print("Erreur de parsing:", e)
                                continue
            finally:
                # Attends que les derniers tokens soient affichés
                await asyncio.sleep(1.2)
                edit_task.cancel()
                try:
                    await edit_task
                except asyncio.CancelledError:
                    pass
                history.append(f"{prompt}\n\nProvidence : {full_text}")
                if len(history) > 5 : history.pop(0)

client.run(TOKEN)
