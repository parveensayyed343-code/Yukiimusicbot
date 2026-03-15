import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)
from pytgcalls import PyTgCalls, idle
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

BOT_TOKEN   = os.getenv("BOT_TOKEN")
API_ID      = int(os.getenv("API_ID", "0"))
API_HASH    = os.getenv("API_HASH", "")
SESSION_STR = os.getenv("SESSION_STRING", "")
OWNER_ID    = int(os.getenv("OWNER_ID", "0"))

queue_mgr = QueueManager()
music_str = MusicStream()
db        = VCDatabase()

userbot = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STR,
    no_updates=True,
)

calls   = PyTgCalls(userbot)
bot_app = None


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def is_admin(func):
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


def player_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause",   callback_data="pause"),
            InlineKeyboardButton("⏭ Skip",    callback_data="skip"),
            InlineKeyboardButton("⏹ Stop",    callback_data="stop"),
        ],
        [
            InlineKeyboardButton("🔁 Loop",    callback_data="loop"),
            InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle"),
            InlineKeyboardButton("📋 Queue",   callback_data="queue"),
        ]
    ])


def resume_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Resume",  callback_data="resume"),
            InlineKeyboardButton("⏭ Skip",    callback_data="skip"),
            InlineKeyboardButton("⏹ Stop",    callback_data="stop"),
        ],
        [
            InlineKeyboardButton("🔁 Loop",    callback_data="loop"),
            InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle"),
            InlineKeyboardButton("📋 Queue",   callback_data="queue"),
        ]
    ])


async def _start_stream(chat_id: int, song: dict):
    """Get stream URL and play via calls.play() — works for both join and change."""
    audio_url = await music_str.get_stream_url(song["url"])
    calls.play(chat_id, MediaStream(audio_url, AudioQuality.HIGH))


async def _send_now_playing(chat_id: int, song: dict):
    if bot_app:
        await bot_app.bot.send_message(
            chat_id,
            f"▶️ *Ab chal raha hai:*\n\n"
            f"🎵 {song['title']}\n"
            f"⏱ {song['duration']}\n"
            f"👤 {song.get('requested_by', 'Unknown')}",
            parse_mode="Markdown",
            reply_markup=player_kb()
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Stream end handler
# ─────────────────────────────────────────────────────────────────────────────
@calls.on_stream_end()
async def stream_ended(client: PyTgCalls, update):
    chat_id = update.chat_id

    if queue_mgr.is_loop(chat_id):
        song = queue_mgr.current(chat_id)
        if song:
            try:
                await _start_stream(chat_id, song)
            except Exception as e:
                logger.error(f"Loop error: {e}")
        return

    queue_mgr.pop(chat_id)
    next_song = queue_mgr.current(chat_id)

    if next_song:
        try:
            await _start_stream(chat_id, next_song)
            await _send_now_playing(chat_id, next_song)
        except Exception as e:
            logger.error(f"Auto next error: {e}")
    else:
        if not db.get_247(chat_id):
            try:
                calls.leave_group_call(chat_id)
            except Exception:
                pass
        if bot_app:
            await bot_app.bot.send_message(
                chat_id, "✅ Queue khatam! `/play` se dobara shuru karo.",
                parse_mode="Markdown"
            )


# ─────────────────────────────────────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎵 *MusicVC Bot*\n\n"
        "Group mein add karo aur `/play` se shuru karo!\n\n"
        "`/play <song/URL>` — Play\n"
        "`/skip` — Next ⏭\n"
        "`/pause` — Pause ⏸\n"
        "`/resume` — Resume ▶️\n"
        "`/stop` — Stop ⏹\n"
        "`/queue` — Queue 📋\n"
        "`/np` — Now Playing 🎧\n"
        "`/volume <1-200>` — Volume 🔊\n"
        "`/loop` — Loop 🔁\n"
        "`/shuffle` — Shuffle 🔀\n"
        "`/247 on/off` — 24/7 mode\n"
    )
    kb = [[InlineKeyboardButton("➕ Group mein Add", url=f"https://t.me/{context.bot.username}?startgroup=true")]]
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
        await update.message.reply_text("❗ Usage: `/play <song name ya URL>`", parse_mode="Markdown")
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
            await msg.edit_text(f"🎵 Connecting...\n*{song_info['title']}*", parse_mode="Markdown")
            try:
                await _start_stream(chat_id, song_info)
                await msg.edit_text(
                    f"▶️ *Playing Now:*\n\n"
                    f"🎵 {song_info['title']}\n"
                    f"⏱ {song_info['duration']}\n"
                    f"👤 {user.first_name}",
                    parse_mode="Markdown",
                    reply_markup=player_kb()
                )
            except Exception as e:
                logger.error(f"Join VC error: {e}")
                queue_mgr.clear(chat_id)
                await msg.edit_text(
                    "❌ Voice Chat join nahi ho saka.\n"
                    "Group mein pehle Voice Chat start karo, phir `/play` karo.",
                    parse_mode="Markdown"
                )
        else:
            await msg.edit_text(
                f"✅ *Queue mein add!*\n\n"
                f"🎵 {song_info['title']}\n"
                f"⏱ {song_info['duration']}\n"
                f"📋 Position: #{position}",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Play error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:150]}")


# ─────────────────────────────────────────────────────────────────────────────
#  Controls
# ─────────────────────────────────────────────────────────────────────────────
@is_admin
async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if queue_mgr.is_empty(chat_id):
        await update.message.reply_text("❌ Queue khaali hai.")
        return
    queue_mgr.pop(chat_id)
    next_song = queue_mgr.current(chat_id)
    if next_song:
        await update.message.reply_text("⏭ Skipping...")
        try:
            await _start_stream(chat_id, next_song)
            await _send_now_playing(chat_id, next_song)
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
    else:
        try:
            calls.leave_group_call(chat_id)
        except Exception:
            pass
        await update.message.reply_text("✅ Queue khatam.")


@is_admin
async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        calls.pause_stream(update.effective_chat.id)
        await update.message.reply_text("⏸ Paused.")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


@is_admin
async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        calls.resume_stream(update.effective_chat.id)
        await update.message.reply_text("▶️ Resumed!")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


@is_admin
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    queue_mgr.clear(chat_id)
    try:
        calls.leave_group_call(chat_id)
    except Exception:
        pass
    await update.message.reply_text("⏹ Stopped!")


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = queue_mgr.get_queue(update.effective_chat.id)
    if not q:
        await update.message.reply_text("📋 Queue khaali hai.", parse_mode="Markdown")
        return
    text = "📋 *Queue:*\n\n"
    for i, s in enumerate(q[:10], 1):
        text += f"{'▶️' if i==1 else str(i)+'.'} *{s['title'][:40]}* — {s['duration']}\n"
    if len(q) > 10:
        text += f"\n_...aur {len(q)-10} songs_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def np_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    song = queue_mgr.current(update.effective_chat.id)
    if not song:
        await update.message.reply_text("❌ Kuch nahi chal raha.")
        return
    await update.message.reply_text(
        f"🎧 *Now Playing:*\n\n🎵 {song['title']}\n⏱ {song['duration']}\n👤 {song.get('requested_by','')}",
        parse_mode="Markdown", reply_markup=player_kb()
    )


@is_admin
async def volume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❗ `/volume <1-200>`", parse_mode="Markdown")
        return
    vol = max(1, min(200, int(context.args[0])))
    try:
        calls.change_volume_call(update.effective_chat.id, vol)
        await update.message.reply_text(f"🔊 Volume: *{vol}%*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def loop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = queue_mgr.toggle_loop(update.effective_chat.id)
    await update.message.reply_text(f"🔁 Loop *{'ON' if state else 'OFF'}*", parse_mode="Markdown")


@is_admin
async def shuffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    queue_mgr.shuffle(update.effective_chat.id)
    await update.message.reply_text("🔀 Shuffled!")


@is_admin
async def clearqueue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    queue_mgr.clear(update.effective_chat.id)
    await update.message.reply_text("🗑 Queue saaf!")


@is_admin
async def mode247_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    arg = context.args[0].lower() if context.args else "on"
    db.set_247(chat_id, arg == "on")
    await update.message.reply_text(f"🕐 24/7 *{'ON' if arg=='on' else 'OFF'}*", parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────────────────────
#  Buttons
# ─────────────────────────────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data    = query.data
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ("administrator", "creator") and user_id != OWNER_ID:
            await query.answer("⛔ Sirf admins!", show_alert=True)
            return
    except Exception:
        pass

    if data == "pause":
        try:
            calls.pause_stream(chat_id)
            await query.edit_message_reply_markup(resume_kb())
        except Exception as e:
            await query.answer(str(e)[:50], show_alert=True)
    elif data == "resume":
        try:
            calls.resume_stream(chat_id)
            await query.edit_message_reply_markup(player_kb())
        except Exception as e:
            await query.answer(str(e)[:50], show_alert=True)
    elif data == "skip":
        queue_mgr.pop(chat_id)
        next_song = queue_mgr.current(chat_id)
        if next_song:
            try:
                await _start_stream(chat_id, next_song)
                await query.edit_message_text(
                    f"▶️ *Now Playing:*\n\n🎵 {next_song['title']}\n⏱ {next_song['duration']}",
                    parse_mode="Markdown", reply_markup=player_kb()
                )
            except Exception as e:
                await query.answer(str(e)[:50], show_alert=True)
        else:
            try:
                calls.leave_group_call(chat_id)
            except Exception:
                pass
            await query.edit_message_text("✅ Queue khatam.")
    elif data == "stop":
        queue_mgr.clear(chat_id)
        try:
            calls.leave_group_call(chat_id)
        except Exception:
            pass
        await query.edit_message_text("⏹ Stopped.")
    elif data == "loop":
        state = queue_mgr.toggle_loop(chat_id)
        await query.answer(f"🔁 Loop {'ON' if state else 'OFF'}")
    elif data == "shuffle":
        queue_mgr.shuffle(chat_id)
        await query.answer("🔀 Shuffled!")
    elif data == "queue":
        q = queue_mgr.get_queue(chat_id)
        if not q:
            await query.answer("Queue khaali!", show_alert=True)
            return
        text = "📋 Queue:\n" + "\n".join(
            f"{'▶️' if i==0 else str(i+1)+'.'} {s['title'][:35]}"
            for i, s in enumerate(q[:8])
        )
        await query.answer(text, show_alert=True)


async def error_handler(update, context):
    logger.error(f"Error: {context.error}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    global bot_app

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set!")
    if not API_ID or not API_HASH:
        raise ValueError("API_ID / API_HASH not set!")
    if not SESSION_STR:
        raise ValueError("SESSION_STRING not set!")

    # Start pyrogram userbot
    await userbot.start()

    # Start PyTgCalls (synchronous in v2.x)
    calls.start()
    logger.info("✅ Userbot + PyTgCalls started.")

    # Build telegram bot
    app = Application.builder().token(BOT_TOKEN).build()
    bot_app = app

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
    app.add_handler(CommandHandler("shuffle",    shuffle_command))
    app.add_handler(CommandHandler("clearqueue", clearqueue_command))
    app.add_handler(CommandHandler("247",        mode247_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("🎵 MusicVC Bot running!")

    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await userbot.stop()


if __name__ == "__main__":
    asyncio.run(main())