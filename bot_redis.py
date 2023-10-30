import asyncio

from redis.asyncio import Redis


TRIGRAM_FACTOR = 10


class BotRedis:
    def __init__(self, host: str, db: int):
        self._host = host
        self._db = db
        self._redis = None
        self._pipe = None

    async def connect(self):
        self._redis = await Redis(host=self._host, port=6379, db=self._db)

    async def init_pipe(self):
        while self._pipe is not None:
            await asyncio.sleep(0.1)
        self._pipe = await self._redis.pipeline()

    async def execute_pipe(self):
        await self._pipe.execute()
        self._pipe = None

    def add_bigram(self, prev, next_):
        self._pipe.sadd(f"bigram:{prev}", next_)
        self._pipe.incr(f"bigram:{prev}:{next_}")

    def add_trigram(self, pprev, prev, next_):
        self._pipe.sadd(f"trigram:{pprev}:{prev}", next_)
        self._pipe.incr(f"trigram:{pprev}:{prev}:{next_}")

    async def get_bigram(self, prev):
        bi_words = await self._redis.smembers(f"bigram:{prev}")
        bi_words = [str(word, "utf-8") for word in bi_words]
        bi_counts = await self._redis.mget(f"bigram:{prev}:{next_}" for next_ in bi_words)
        bi_counts = [int(i) for i in bi_counts]
        assert len(bi_words) == len(bi_counts)
        return bi_words, bi_counts

    async def get_trigram(self, pprev, prev):
        tri_words = await self._redis.smembers(f"trigram:{pprev}:{prev}")
        tri_words = [str(word, "utf-8") for word in tri_words]
        tri_counts = await self._redis.mget(f"trigram:{pprev}:{prev}:{next_}" for next_ in tri_words)
        tri_counts = [int(i) * TRIGRAM_FACTOR for i in tri_counts]
        assert len(tri_words) == len(tri_counts)
        return tri_words, tri_counts
