import os
from pyrogram import Client, filters

API_ID = int(os.getenv("38581374"))
API_HASH = os.getenv("593b7c5cede2acd45c7480f9fa4b2451")
BOT_TOKEN = os.getenv("8101218773:AAGly_-QxQ-SUlp0CKtnk_zbRYwUJoytCNg")

app = Client("music_bot", api_id=38581374, api_hash=593b7c5cede2acd45c7480f9fa4b2451, bot_token=8101218773:AAGly_-QxQ-SUlp0CKtnk_zbRYwUJoytCNg)

@app.on_message(filters.command("start"))
def start(client, message):
    message.reply("🎵 Bot Ready!")

app.run()
