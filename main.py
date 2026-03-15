import asyncio
from keep_alive import start_keep_alive
from bot import main

if __name__ == "__main__":
    start_keep_alive()
    asyncio.run(main())