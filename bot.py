import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality
from pyrogram import Client
from queue_manager import QueueManager
from music_stream import MusicStream
from database import VCDatabase

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── ENV ───────────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN")
API_ID      = int(os.getenv("API_ID", "0"))
API_HASH    = os.getenv("API_HASH", "")
SESSION_STR = os.getenv("SESSION_STRING", "")   # Pyrogram StringSession
OWNER_ID    = int(os.getenv("OWNER_ID", "0"))

# ── Core objects ──────────────────────────────────────────────────────────────
queue_mgr   = QueueManager()
music_str   = MusicStream()
db          = VCDatabase()

# Pyrogram userbot client (joins VC)
userbot = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STR,
    no_updates=True,
)

calls = PyTgCalls(userbot)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def is_admin(func):
    """Decorator: only group admins / owner can use this command."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if user_id == OWNER_ID:
            return await func(update, context)
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ("administrator", "creator"):
                return await func(update, context)
        except Exception:
            pass
        await update.message.reply_text("⛔ Sirf admins ye command use kar sakte hain.")
    return wrapper


async def play_next(chat_id: int, context):
    """Play next song from queue."""
    song = queue_mgr.next(chat_id)
    if not song:
        await context.bot.send_message(chat_id, "✅ Queue khatam ho gayi. Phir `/play` karo!")
        return

    await context.bot.send_message(
        chat_id,
        f"▶️ *Ab chal raha hai:*\n🎵 {song['title']}\n⏱ {song['duration']}\n👤 Requested by: {song['requested_by']}",
        parse_mode="Markdown"
    )

    try:
        audio_url = await music_str.get_stream_url(song["url"])
        await calls.change_stream(
            chat_id,
            MediaStream(audio_url, audio_quality=AudioQuality.HIGH)
        )
    except Exception as e:
        logger.error(f"play_next error: {e}")
        await asyncio.sleep(2)
        await play_next(chat_id, context)


# ─────────────────────────────────────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎵 *MusicVC Bot — Voice Chat Music Player*\n\n"
        "Mujhe apne group mein add karo aur `/play` se shuru karo!\n\n"
        "*Commands:*\n"
        "`/play <song/URL>` — Queue mein add & play karo\n"
        "`/skip` — Next song ⏭\n"
        "`/pause` — Pause ⏸\n"
        "`/resume` — Resume ▶️\n"
        "`/stop` — Stop & VC se niklo ⏹\n"
        "`/queue` — Queue dekho 📋\n"
        "`/np` — Abhi kya chal raha hai 🎧\n"
        "`/volume <1-200>` — Volume set karo 🔊\n"
        "`/loop` — Loop on/off 🔁\n"
        "`/shuffle` — Queue shuffle karo 🔀\n"
        "`/clearqueue` — Queue saaf karo 🗑\n"
        "`/247 on/off` — 24/7 mode (Admin only) 🕐\n"
    )
    kb = [[InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# ─────────────────────────────────────────────────────────────────────────────
#  /play
# ─────────────────────────────────────────────────────────────────────────────
async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user    = update.effective_user

    if update.effective_chat.type == "private":
        await update.message.reply_text("❗ Ye command group mein use karo.")
        return

    if not context.args:
        await update.message.reply_text("❗ Usage: `/play <song name ya YouTube URL>`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    msg   = await update.message.reply_text(f"🔍 Dhundh raha hoon: *{query}*...", parse_mode="Markdown")

    try:
        song_info = await music_str.search_and_get_info(query)
        if not song_info:
            await msg.edit_text("❌ Koi result nahi mila.")
            return

        song_info["requested_by"] = user.first_name
        position = queue_mgr.add(chat_id, song_info)

        if position == 1:
            # Bot VC mein join karo aur play karo
            await msg.edit_text(f"🎵 Connecting to Voice Chat...\n*{song_info['title']}*", parse_mode="Markdown")
            try:
                audio_url = await music_str.get_stream_url(song_info["url"])
                await calls.join_group_call(
                    chat_id,
                    MediaStream(audio_url, audio_quality=AudioQuality.HIGH)
                )
                await msg.edit_text(
                    f"▶️ *Playing Now:*\n\n"
                    f"🎵 {song_info['title']}\n"
                    f"⏱ {song_info['duration']}\n"
                    f"👤 {user.first_name}",
                    parse_mode="Markdown",
                    reply_markup=player_keyboard()
                )
            except Exception as e:
                logger.error(f"Join VC error: {e}")
                if "already" in str(e).lower():
                    # Already in VC, change stream
                    audio_url = await music_str.get_stream_url(song_info["url"])
                    await calls.change_stream(
                        chat_id,
                        MediaStream(audio_url, audio_quality=AudioQuality.HIGH)
                    )
                    await msg.edit_text(
                        f"▶️ *Playing Now:*\n\n🎵 {song_info['title']}\n⏱ {song_info['duration']}",
                        parse_mode="Markdown",
                        reply_markup=player_keyboard()
                    )
                else:
                    queue_mgr.clear(chat_id)
                    await msg.edit_text(
                        "❌ Voice Chat mein join nahi ho saka.\n"
                        "Pehle group mein Voice Chat shuru karo, phir `/play` karo.",
                        parse_mode="Markdown"
                    )
        else:
            await msg.edit_text(
                f"✅ *Queue mein add ho gaya!*\n\n"
                f"🎵 {song_info['title']}\n"
                f"⏱ {song_info['duration']}\n"
                f"📋 Position: #{position}",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Play error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:150]}")


def player_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data="pause"),
            InlineKeyboardButton("⏭ Skip",  callback_data="skip"),
            InlineKeyboardButton("⏹ Stop",  callback_data="stop"),
        ],
        [
            InlineKeyboardButton("🔁 Loop",    callback_data="loop"),
            InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle"),
            InlineKeyboardButton("📋 Queue",   callback_data="queue"),
        ]
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  /skip
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if queue_mgr.is_empty(chat_id):
        await update.message.reply_text("❌ Queue khaali hai.")
        return
    await update.message.reply_text("⏭ Skipping...")
    await play_next(chat_id, context)


# ─────────────────────────────────────────────────────────────────────────────
#  /pause
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await calls.pause_stream(chat_id)
        await update.message.reply_text("⏸ Music pause ho gaya.\n`/resume` se wapas chalao.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  /resume
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await calls.resume_stream(chat_id)
        await update.message.reply_text("▶️ Music resume ho gaya!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  /stop
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        queue_mgr.clear(chat_id)
        await calls.leave_group_call(chat_id)
        await update.message.reply_text("⏹ Music stop ho gaya aur VC se nikal gaya.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  /queue
# ─────────────────────────────────────────────────────────────────────────────
async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    q = queue_mgr.get_queue(chat_id)

    if not q:
        await update.message.reply_text("📋 Queue khaali hai. `/play` se song add karo!", parse_mode="Markdown")
        return

    text = "📋 *Current Queue:*\n\n"
    for i, song in enumerate(q[:10], 1):
        prefix = "▶️" if i == 1 else f"{i}."
        text += f"{prefix} *{song['title'][:40]}* — {song['duration']}\n"

    if len(q) > 10:
        text += f"\n_...aur {len(q)-10} songs_"

    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────────────────────
#  /np  (Now Playing)
# ─────────────────────────────────────────────────────────────────────────────
async def np_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    song = queue_mgr.current(chat_id)
    if not song:
        await update.message.reply_text("❌ Koi song nahi chal raha.")
        return
    await update.message.reply_text(
        f"🎧 *Now Playing:*\n\n"
        f"🎵 {song['title']}\n"
        f"⏱ {song['duration']}\n"
        f"👤 Requested by: {song['requested_by']}",
        parse_mode="Markdown",
        reply_markup=player_keyboard()
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /volume
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def volume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❗ Usage: `/volume <1-200>`", parse_mode="Markdown")
        return
    vol = max(1, min(200, int(context.args[0])))
    try:
        await calls.change_volume_call(chat_id, vol)
        await update.message.reply_text(f"🔊 Volume set to *{vol}%*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  /loop
# ─────────────────────────────────────────────────────────────────────────────
async def loop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = queue_mgr.toggle_loop(chat_id)
    emoji = "🔁" if state else "➡️"
    await update.message.reply_text(f"{emoji} Loop *{'ON' if state else 'OFF'}*", parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────────────────────
#  /shuffle
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def shuffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    queue_mgr.shuffle(chat_id)
    await update.message.reply_text("🔀 Queue shuffle ho gayi!")


# ─────────────────────────────────────────────────────────────────────────────
#  /clearqueue
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def clearqueue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    queue_mgr.clear(chat_id)
    await update.message.reply_text("🗑 Queue saaf ho gayi!")


# ─────────────────────────────────────────────────────────────────────────────
#  /247
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def mode247_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    arg = context.args[0].lower() if context.args else "on"
    if arg == "on":
        db.set_247(chat_id, True)
        await update.message.reply_text(
            "🕐 *24/7 Mode ON!*\n\nBot VC mein connected rahega, chahe queue khaali ho.",
            parse_mode="Markdown"
        )
    else:
        db.set_247(chat_id, False)
        await update.message.reply_text("✅ 24/7 Mode OFF.")


# ─────────────────────────────────────────────────────────────────────────────
#  Callback buttons (inline keyboard)
# ─────────────────────────────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data    = query.data
    user_id = query.from_user.id

    # Check admin
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ("administrator", "creator") and user_id != OWNER_ID:
            await query.answer("⛔ Sirf admins use kar sakte hain!", show_alert=True)
            return
    except Exception:
        pass

    if data == "pause":
        try:
            await calls.pause_stream(chat_id)
            await query.edit_message_reply_markup(resume_keyboard())
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

    elif data == "resume":
        try:
            await calls.resume_stream(chat_id)
            await query.edit_message_reply_markup(player_keyboard())
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

    elif data == "skip":
        await play_next(chat_id, context)
        await query.answer("⏭ Skipped!")

    elif data == "stop":
        queue_mgr.clear(chat_id)
        try:
            await calls.leave_group_call(chat_id)
        except Exception:
            pass
        await query.edit_message_text("⏹ Music stop ho gaya.")

    elif data == "loop":
        state = queue_mgr.toggle_loop(chat_id)
        await query.answer(f"🔁 Loop {'ON' if state else 'OFF'}")

    elif data == "shuffle":
        queue_mgr.shuffle(chat_id)
        await query.answer("🔀 Queue shuffled!")

    elif data == "queue":
        q = queue_mgr.get_queue(chat_id)
        if not q:
            await query.answer("Queue khaali hai!", show_alert=True)
            return
        text = "📋 Queue:\n" + "\n".join(
            f"{'▶️' if i==0 else str(i+1)+'.'} {s['title'][:35]}"
            for i, s in enumerate(q[:8])
        )
        await query.answer(text, show_alert=True)


def resume_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Resume", callback_data="resume"),
            InlineKeyboardButton("⏭ Skip",   callback_data="skip"),
            InlineKeyboardButton("⏹ Stop",   callback_data="stop"),
        ],
        [
            InlineKeyboardButton("🔁 Loop",    callback_data="loop"),
            InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle"),
            InlineKeyboardButton("📋 Queue",   callback_data="queue"),
        ]
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  PyTgCalls stream end handler → auto play next
# ─────────────────────────────────────────────────────────────────────────────
@calls.on_stream_end()
async def stream_end_handler(client, update):
    chat_id = update.chat_id
    loop_on = queue_mgr.is_loop(chat_id)

    if loop_on:
        song = queue_mgr.current(chat_id)
        if song:
            try:
                audio_url = await music_str.get_stream_url(song["url"])
                await calls.change_stream(
                    chat_id,
                    MediaStream(audio_url, audio_quality=AudioQuality.HIGH)
                )
            except Exception as e:
                logger.error(f"Loop replay error: {e}")
        return

    # Remove current and play next
    queue_mgr.pop(chat_id)
    next_song = queue_mgr.current(chat_id)

    if next_song:
        try:
            audio_url = await music_str.get_stream_url(next_song["url"])
            await calls.change_stream(
                chat_id,
                MediaStream(audio_url, audio_quality=AudioQuality.HIGH)
            )
        except Exception as e:
            logger.error(f"Auto next error: {e}")
    else:
        if not db.get_247(chat_id):
            try:
                await calls.leave_group_call(chat_id)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
#  Error handler
# ─────────────────────────────────────────────────────────────────────────────
async def error_handler(update, context):
    logger.error(f"Error: {context.error}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set!")
    if not API_ID or not API_HASH:
        raise ValueError("API_ID / API_HASH not set!")
    if not SESSION_STR:
        raise ValueError("SESSION_STRING not set! Run generate_session.py first.")

    # Start userbot + PyTgCalls
    await userbot.start()
    await calls.start()
    logger.info("Userbot + PyTgCalls started.")

    # Build bot application
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("play",       play_command))
    app.add_handler(CommandHandler("skip",       skip_command))
    app.add_handler(CommandHandler("pause",      pause_command))
    app.add_handler(CommandHandler("resume",     resume_command))
    app.add_handler(CommandHandler("stop",       stop_command))
    app.add_handler(CommandHandler("queue",      queue_command))
    app.add_handler(CommandHandler("np",         np_command))
    app.add_handler(CommandHandler("volume",     volume_command))
    app.add_handler(CommandHandler("loop",       loop_command))
    app.add_handler(CommandHan