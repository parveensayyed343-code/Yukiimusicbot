import asyncio
import logging
import yt_dlp

logger = logging.getLogger(__name__)


class MusicStream:
    """
    Uses yt-dlp to search YouTube and extract direct stream URLs.
    No files are downloaded — pure streaming URLs are passed to PyTgCalls.
    """

    def _ydl_opts(self) -> dict:
        return {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "noplaylist": True,
        }

    # ── Search + get info ─────────────────────────────────────────────────────
    async def search_and_get_info(self, query: str) -> dict | None:
        def _run():
            opts = {**self._ydl_opts(), "extract_flat": False}

            # If it's a URL, use directly; otherwise search YouTube
            if query.startswith("http"):
                search_query = query
            else:
                search_query = f"ytsearch1:{query}"

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(search_query, download=False)
                    if not info:
                        return None

                    # ytsearch returns a list
                    if "entries" in info:
                        info = info["entries"][0]
                        if not info:
                            return None

                    duration_sec = info.get("duration", 0) or 0
                    minutes = int(duration_sec // 60)
                    seconds = int(duration_sec % 60)

                    return {
                        "id":       info.get("id", ""),
                        "title":    info.get("title", "Unknown"),
                        "url":      info.get("webpage_url") or info.get("url", ""),
                        "duration": f"{minutes}:{seconds:02d}",
                        "thumbnail": info.get("thumbnail", ""),
                        "uploader": info.get("uploader", "Unknown"),
                    }
                except Exception as e:
                    logger.error(f"search error: {e}")
                    return None

        return await asyncio.get_event_loop().run_in_executor(None, _run)

    # ── Get actual audio stream URL ───────────────────────────────────────────
    async def get_stream_url(self, webpage_url: str) -> str:
        def _run():
            opts = {**self._ydl_opts()}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(webpage_url, download=False)
                if not info:
                    raise ValueError("Could not extract stream URL")

                # Get the best audio format URL
                formats = info.get("formats", [])
                audio_formats = [
                    f for f in formats
                    if f.get("acodec") != "none" and f.get("vcodec") == "none"
                ]

                if audio_formats:
                    # Pick highest quality audio-only
                    best = max(audio_formats, key=lambda f: f.get("abr", 0) or 0)
                    return best["url"]

                # Fallback: use direct url
                return info.get("url", "")

        return await asyncio.get_event_loop().run_in_executor(None, _run)