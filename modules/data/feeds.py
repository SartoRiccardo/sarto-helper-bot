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
    :return: bool
    """
    return await get_feed(feed_name) is not None


async def get_feed(feed_name, ignore_case=True):
    """
    Return a feed, searching it by its name.
    :param feed_name: str: The name of the feed to check.
    :param ignore_case: bool: Makes the research case insensitive.
    :return: Feed: The match, or None.
    """
    path = await modules.data.owner.get_config(DISCORDBOORU_PATH_KEY)
    if path is None:
        return None

    fin = open(path + DISCORDBOORU_FEEDS_PATH)
    found = None
    for feed in json.load(fin):
        if ignore_case and feed["name"].lower() == feed_name.lower() or \
                not ignore_case and feed["name"] == feed_name:
            found = Feed(json=feed)
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


async def delete_feed(name):
    """
    Deletes a feed by its name
    :param name: str: The name of the feed to delete.
    """
    path = await modules.data.owner.get_config(DISCORDBOORU_PATH_KEY)
    if path is None:
        return None

    with open(path + DISCORDBOORU_FEEDS_PATH) as fin:
        feeds = json.load(fin)

    feeds = [feed for feed in feeds if feed["name"].lower() != name.lower()]

    try:
        with open(path + DISCORDBOORU_FEEDS_PATH, "w") as fout:
                json.dump(feeds, fout)
    except:
        pass


async def edit_feed(feed_name: str, new_feed: Feed):
    """
    Replaces a feed with the new one.
    :param feed_name: str: The name of the feed to edit.
    :param new_feed: Feed: The new version of the feed.
    """
    path = await modules.data.owner.get_config(DISCORDBOORU_PATH_KEY)
    if path is None:
        return None

    with open(path + DISCORDBOORU_FEEDS_PATH) as fin:
        feeds = json.load(fin)

    for i in range(len(feeds)):
        feed = feeds[i]
        if feed["name"].lower() != feed_name.lower():
            continue

        feeds[i] = new_feed.dict()

    try:
        with open(path + DISCORDBOORU_FEEDS_PATH, "w") as fout:
                json.dump(feeds, fout)
    except:
        pass
