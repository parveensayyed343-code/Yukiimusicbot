"""
generate_session.py
───────────────────
Run this script ONCE on your local machine to generate a Pyrogram
StringSession. Copy the output and set it as SESSION_STRING env var on Render.

Usage:
    python generate_session.py
"""

import asyncio
from hydrogram import Client



async def generate():
    print("=" * 50)
    print("  Pyrogram StringSession Generator")
    print("=" * 50)
    print()
    print("Apna API_ID aur API_HASH enter karo.")
    print("Ye my.telegram.org se milega (free).")
    print()

    api_id   = int(input("API_ID   : ").strip())
    api_hash = input("API_HASH : ").strip()

    async with Client(
        "session_gen",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    ) as app:
        print()
        print("✅ Login successful!")
        session = await app.export_session_string()
        print()
        print("=" * 50)
        print("YOUR SESSION STRING (copy this):")
        print("=" * 50)
        print(session)
        print("=" * 50)
        print()
        print("Is session string ko Render mein SESSION_STRING env var mein paste karo.")


if __name__ == "__main__":
    asyncio.run(generate())