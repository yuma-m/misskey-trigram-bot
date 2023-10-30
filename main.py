import asyncio
import os

from bot import MisskeyBot


def main():
    redis_host = os.getenv("REDIS_HOST")
    redis_db = int(os.getenv("REDIS_DB"))
    url = os.getenv("SERVER_URL")
    token = os.getenv("API_TOKEN")
    interval = int(os.getenv("SPEAK_INTERVAL"))

    bot = MisskeyBot(redis_host, redis_db, interval)
    asyncio.run(bot.start_wrapper(url, token))


if __name__ == '__main__':
    main()
