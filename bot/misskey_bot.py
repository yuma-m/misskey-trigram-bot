import asyncio
import logging
import random
import re
from collections import deque

from aiohttp import ClientWebSocketResponse
from janome.tokenizer import Tokenizer
from mipa.ext.commands.bot import Bot
from mipac import Note

from bot.bot_redis import BotRedis

END_TOKEN = ":END:"

RE_ENGLISH_ONLY = r"[a-zA-Z -/:-@[-´{-~]+"
RE_REACTION = r":[a-z0-9_]+:"


class MisskeyBot(Bot):
    def __init__(self, redis_host, redis_db, interval):
        super().__init__()
        self.tokenizer = Tokenizer()
        self.db = BotRedis(redis_host, redis_db)
        self.logger = self._setup_logger()
        self.topic_queue = deque(maxlen=100)
        self.speak_interval = interval

    @staticmethod
    def _setup_logger():
        logger = logging.getLogger("MisskeyBot")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s - %(message)s"))
        logger.addHandler(handler)
        return logger

    async def _connect_channel(self):
        await self.router.connect_channel(['local'])
        self.logger.debug(f'Connected to local channel')

    async def on_ready(self, ws: ClientWebSocketResponse):
        self.logger.info(f'Logged in as {self.user.username}')
        await self.db.connect()
        await self._connect_channel()

    async def on_reconnect(self, ws: ClientWebSocketResponse):
        await self._connect_channel()

    async def on_note(self, note: Note):
        if self._should_not_learn(note):
            return
        self.logger.debug(f"Note: {note.content}")
        words, nouns = self._parse(note.content)
        await self._learn_words(words)
        for n in set(nouns):
            self.topic_queue.append(n)

    @staticmethod
    def _should_not_learn(note: Note):
        return (not note.content
                or note.cw is not None
                or note.content.find("play/") > 0)

    def _parse(self, msg):
        def tokenize(text):
            words_, nouns_ = [], []
            for token in self.tokenizer.tokenize(text):
                surface = token.surface
                if not re.match(RE_ENGLISH_ONLY, surface):
                    words_.append(surface)
                    if token.part_of_speech.startswith("名詞"):
                        nouns_.append(surface)
            return words_, nouns_

        words, nouns = [], []
        cursor = 0
        for line in msg.splitlines():
            for match in re.finditer(RE_REACTION, line):
                w, n = tokenize(line[cursor:match.start(0)])
                words.extend(w)
                nouns.extend(n)
                reaction = match.group(0)
                words.append(reaction)
                nouns.append(reaction)
                cursor = match.end(0)
            w, n = tokenize(line[cursor:])
            words.extend(w)
            nouns.extend(n)
        return words, nouns

    async def _learn_words(self, words):
        words = words + [END_TOKEN]
        await self.db.init_pipe()
        for i in range(len(words) - 1):
            prev, next_ = words[i], words[i + 1]
            self.db.add_bigram(prev, next_)
            if i >= 1:
                pprev = words[i - 1]
                self.db.add_trigram(pprev, prev, next_)
        await self.db.execute_pipe()

    def _choose_from_recent_topics(self):
        if not self.topic_queue:
            return
        topic = random.choice(self.topic_queue)
        return topic

    async def _choose_next_word(self, prev, pprev):
        bi_words, bi_counts = await self.db.get_bigram(prev)
        if pprev:
            tri_words, tri_counts = await self.db.get_trigram(pprev, prev)
        else:
            tri_words, tri_counts = [], []
        if not (bi_words or tri_words):
            return
        counts = tri_counts + bi_counts
        sum_ = sum(counts)
        dcr = random.randrange(0, sum_)
        for i, c in enumerate(counts):
            dcr -= c
            if dcr < 0:
                if i < len(tri_counts):
                    return tri_words[i]
                return bi_words[i - len(tri_counts)]

    async def _generate_message(self, initial, min_words=10, max_words=20):
        length = min_words + random.randrange(0, max_words - min_words)
        msg = ["", initial]
        for _ in range(length):
            next_ = await self._choose_next_word(msg[-1], msg[-2])
            if not next_ or next_ == END_TOKEN:
                break
            msg.append(next_)
        msg = "".join(msg)
        return msg

    async def _speak(self):
        topic = self._choose_from_recent_topics()
        if not topic:
            self.logger.warning(f"Couldn't create a note: Recent topics not found")
            return
        msg = await self._generate_message(topic)
        self.logger.info(f"Create a note: {msg}")
        await self.client.note.action.send(content=msg)

    async def speak_loop(self):
        while True:
            await asyncio.sleep(self.speak_interval)
            await self._speak()

    async def start_wrapper(self, url, token):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.start(url, token))
            tg.create_task(self.speak_loop())
