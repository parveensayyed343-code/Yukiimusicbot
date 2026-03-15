import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "🎵 MusicVC Bot is alive!", 200

@app.route("/health")
def health():
    return {"status": "ok", "bot": "MusicVC Bot"}, 200

def run():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

def start_keep_alive():
    t = threading.Thread(target=run, daemon=True)
    t.start()