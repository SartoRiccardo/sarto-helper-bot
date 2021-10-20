from modules.data.connection import postgres
from modules.data.models import Feed
import json
import modules.data.owner

DISCORDBOORU_PATH_KEY = "feeds-path"
DISCORDBOORU_FEEDS_PATH = "feeds.json"


async def get_feeds(owner=None):
    """
    Get a list of feeds.
    :param owner: int: The ID of the discord user who owns the feeds.
    :return: List<Feed>: A list of feeds.
    """
    path = await modules.data.owner.get_config(DISCORDBOORU_PATH_KEY)
    if path is None:
        return None

    fin = open(path + DISCORDBOORU_FEEDS_PATH)
    feeds = [Feed(json=f) for f in json.load(fin)]
    fin.close()

    if owner is not None:
        for i in range(len(feeds), -1, -1):
            f = feeds[i]
            if owner != f.owner:
                feeds.pop(i)

    return feeds


async def exists(feed_name):
    """
    Return whether the feed name exists or not.
    :param feed_name: str: The name of the feed to check.
    :return: bool:
    """
    path = await modules.data.owner.get_config(DISCORDBOORU_PATH_KEY)
    if path is None:
        return None

    fin = open(path + DISCORDBOORU_FEEDS_PATH)
    found = False
    for feed in json.load(fin):
        if feed["name"] == feed_name:
            found = True
            break
    fin.close()

    return found


async def add_feed(feed):
    if await exists(feed.name):
        return

    path = await modules.data.owner.get_config(DISCORDBOORU_PATH_KEY)
    if path is None:
        return None

    with open(path + DISCORDBOORU_FEEDS_PATH) as fin:
        feeds = json.load(fin)
        feeds.append(feed.dict())
    with open(path + DISCORDBOORU_FEEDS_PATH, "w") as fout:
        try:
            json.dump(feeds, fout)
        except:
            fout.write("[]")


async def delete_feed(id):
    pass


async def edit_feed(feed, changes):
    pass
