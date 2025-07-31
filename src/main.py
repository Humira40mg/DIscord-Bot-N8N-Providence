import discord
import asyncio
import aiohttp
from dotenv import load_dotenv
import os
import json
import time
from logger import logger

load_dotenv()

TOKEN = os.getenv("TOKEN")
N8N_ENDPOINT = 'http://localhost:5678/webhook/jokso' 

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

lock = asyncio.Lock()
history = []
queue:list = []
model = "qwen3:0.6b"

@client.event
async def on_ready():
    print(f'Connecté en tant que {client.user}!')

@client.event
async def on_message(message):
    if message.author == client : return

    if message.channel.id == 1398833482234466456 or (message.content.startswith(".agent") and message.author.id == 254115104210026497):
        logger.info("Demande d'intervation de Providence en mode Agent.")
        async with message.channel.typing():
            async with lock:
                try:
                    async with aiohttp.ClientSession() as session:
                        payload = {'message': message.content, 'id': str(message.author.id)}
                        #TODO : logger + is typing
                        async with session.post(N8N_ENDPOINT, json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                await message.reply(f"{data.get('output')}")
                            else:
                                await message.reply(f"Désolé j'ai rencontré une erreur sur mon chemain. {resp.status}")
                                logger.warn(f"Request Status not 200 : {resp.status}")
                except Exception as e:
                    await message.reply(f"Erreur : {e}")
                    logger.error(f"Erreur : {e}")
        return

    elif client.user in message.mentions :
        if message.author in queue : 
            await message.reply("Je suis un peu surchargé peux tu patienter un peu stp ? c: (Ta réponse arrive).")
            return
        
        queue.append(message.author)
        async with message.channel.typing():
            async with lock:

                history.append({"role": message.author.name, "message":message.content})
                if len(history) > 5 : 
                    history.pop(0)
                    history.pop(0)

                payload = {
                    "model": model,
                    "messages": history,
                    "stream": True
                }
                
                logger.info(f"Demande d'intervation de Providence en mode PUBLIC par {message.author.mention}")
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
                            full_text = full_text.replace("<think>", " **Raisonnement : **\n```\n")
                            if not "</think>" in full_text:
                                await reply.edit(content=full_text[:1995] + "\n```")
                            else:
                                full_text = full_text.replace("</think>", "```")
                                await reply.edit(content=full_text[:2000])
                        await asyncio.sleep(0.5)

                edit_task = asyncio.create_task(periodic_edit())

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(f"http://localhost:11434/api/chat", json=payload) as resp:
                            if resp.status != 200:
                                await reply.edit(content="Erreur lors de la génération.")
                                logger.warn(f"Request Status not 200 : {resp.status}")
                                return

                            async for line in resp.content:
                                if not line.strip():
                                    continue
                                try:
                                    data = json.loads(line.decode("utf-8"))
                                    token = data.get("response", "")
                                    buffer.append(token)  # On ajoute au buffer
                                except Exception as e:
                                    logger.error(f"Erreur : {e}")
                                    continue
                finally:
                    # Attends que les derniers tokens soient affichés
                    await asyncio.sleep(1.2)
                    edit_task.cancel()
                    try:
                        await edit_task
                    except asyncio.CancelledError:
                        pass
                    history.append({"role": "Providence", "content": full_text})
                    queue.remove(message.author)
            return

client.run(TOKEN)
