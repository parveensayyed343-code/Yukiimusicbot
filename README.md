# 🎵 MusicVC Bot — Telegram Voice Chat Music Bot

Group ke Voice Chat mein music play karne wala **advanced, fully free** Telegram bot.
Render Free Tier + UptimeRobot = **24/7 free hosting!**

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🎵 YouTube Playback | Direct stream — koi file download nahi |
| 📋 Queue System | Unlimited songs queue kar sako |
| ⏸ Admin Controls | Pause / Resume / Skip / Stop / Volume |
| 🔁 Loop Mode | Current song repeat karo |
| 🔀 Shuffle | Queue ko shuffle karo |
| 🕐 24/7 Mode | VC mein connected raho chahe queue khaali ho |
| 🎛 Inline Buttons | Touch-friendly player controls |
| 💾 Persistent DB | SQLite with Render disk |

---

## 🛠️ Required Cheezein (Collect Karo Pehle)

Tumhe **5 cheezein** chahiye deploy karne se pehle:

| Kya | Kahan Se |
|---|---|
| `BOT_TOKEN` | @BotFather (Telegram) |
| `API_ID` | my.telegram.org |
| `API_HASH` | my.telegram.org |
| `SESSION_STRING` | `generate_session.py` run karo |
| `OWNER_ID` | @userinfobot (Telegram) |

---

## 🚀 Step-by-Step Deployment

---

### ✅ STEP 1 — Bot Token (BotFather)

1. Telegram → **@BotFather** → `/newbot`
2. Name: `MusicVC Bot`
3. Username: `yourmusicvcbot`
4. **Token copy karo** → `123456:ABCxyz...`

---

### ✅ STEP 2 — API ID & API Hash (my.telegram.org)

> ⚠️ Ye ZAROORI hai — bina iske bot Voice Chat join nahi kar sakta!

1. Browser mein jao: **https://my.telegram.org**
2. Phone number se login karo
3. **"API Development Tools"** click karo
4. App name: `MusicVCBot` | Platform: `Other`
5. **`api_id`** aur **`api_hash`** copy karo

---

### ✅ STEP 3 — Session String Generate Karo (Local Machine)

Session string ek "login token" hai jo bot ko Telegram account se join karwata hai.

```bash
# Apne computer pe run karo (ek baar hi)
pip install pyrogram TgCrypto
python generate_session.py
```

- Phone number enter karo
- OTP enter karo
- 2FA password (agar laga hai)
- **Lamba string copy karo** — ye SESSION_STRING hai

> 💡 Tip: Ek **alag/secondary Telegram account** use karo — main account nahi.

---

### ✅ STEP 4 — Owner ID Lo

1. Telegram → **@userinfobot** → `/start`
2. Apna **numeric ID** copy karo (e.g. `987654321`)

---

### ✅ STEP 5 — GitHub pe Push Karo

```bash
git init
git add .
git commit -m "MusicVC Bot init"
git branch -M main
git remote add origin https://github.com/TUMHARA_USERNAME/vc-music-bot.git
git push -u origin main
```

---

### ✅ STEP 6 — Render pe Deploy (Free)

1. **https://render.com** → Sign up / Login
2. **New + → Web Service**
3. GitHub repo connect karo
4. Settings:
   - **Environment:** `Docker`
   - **Branch:** `main`
   - **Plan:** `Free`
5. **Advanced → Add Environment Variables:**

| Key | Value |
|---|---|
| `BOT_TOKEN` | Step 1 ka token |
| `API_ID` | Step 2 ka API ID |
| `API_HASH` | Step 2 ka API Hash |
| `SESSION_STRING` | Step 3 ka string |
| `OWNER_ID` | Step 4 ka ID |
| `PORT` | `8080` |

6. **"Add Disk"** (optional but recommended for 24/7 persistence):
   - Name: `vcbot-data`
   - Mount Path: `/app/data`
   - Size: `1 GB`
7. **Create Web Service** → Build hoga (~5 min)

---

### ✅ STEP 7 — UptimeRobot (24/7 Alive — Free)

1. **https://uptimerobot.com** → Sign up (free)
2. **Add New Monitor → HTTP(s)**
3. URL: `https://YOUR-APP.onrender.com/health`
4. Interval: **5 minutes**
5. Save ✅

---

### ✅ STEP 8 — Group Setup

1. Bot ko apne group mein add karo
2. Bot ko **Admin** banao (important!)
3. Group mein **Voice Chat shuru karo** (3 dots → Start Voice Chat)
4. `/play <song name>` type karo → Bot VC join karega aur play karega! 🎵

---

## 📋 All Commands

```
/play <song/URL>    — Song search & play karo
/skip               — Next song (Admin)
/pause              — Pause karo (Admin)
/resume             — Resume karo (Admin)
/stop               — Stop & VC se niklo (Admin)
/queue              — Queue dekho
/np                 — Ab kya chal raha hai
/volume <1-200>     — Volume set karo (Admin)
/loop               — Loop on/off toggle
/shuffle            — Queue shuffle karo (Admin)
/clearqueue         — Poori queue saaf karo (Admin)
/247 on/off         — 24/7 mode toggle (Admin)
```

---

## 🗂️ Project Structure

```
vc-music-bot/
├── main.py              ← Entry point
├── bot.py               ← All handlers + PyTgCalls logic
├── music_stream.py      ← yt-dlp stream URL fetcher
├── queue_manager.py     ← Per-chat queue + loop + shuffle
├── database.py          ← SQLite (24/7 mode)
├── keep_alive.py        ← Flask keep-alive server
├── generate_session.py  ← Run ONCE to get SESSION_STRING
├── requirements.txt
├── Dockerfile
└── .gitignore
```

---

## ⚠️ Important Notes

- **Secondary account use karo** for SESSION_STRING — main account use karna risky ho sakta hai
- Voice Chat **pehle start hona chahiye** group mein before `/play`
- Render free tier mein **750 hrs/month** — UptimeRobot ke saath 24/7 chalega
- yt-dlp se direct stream hota hai — **koi file save nahi hoti** (disk bachti hai)

---

## 🔧 Local Testing

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# ffmpeg install karo:
# Ubuntu: sudo apt install ffmpeg
# Mac:    brew install ffmpeg

export BOT_TOKEN="..."
export API_ID="..."
export API_HASH="..."
export SESSION_STRING="..."
export OWNER_ID="..."

python main.py
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| "SESSION_STRING not set" | `generate_session.py` run karo |
| Bot VC mein join nahi hota | Group mein VC start karo + Bot ko admin banao |
| "FloodWait" error | Thodi der ruko, Telegram rate limit |
| Build fail on Render | Render logs check karo — env vars sahi hain? |
| Bot sleeps | UptimeRobot setup karo (Step 7) |