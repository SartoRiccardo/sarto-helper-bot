import json


class Feed:
    SFW = 0
    NSFW = 1
    BOTH = 2

    def __init__(self, **kwargs):
        self.owner = None
        self.name = ""
        self.tags = []
        self.webhook = ""
        self.blacklist = []
        self.color = "000000"
        self.rating = Feed.SFW

        if "json" in kwargs:
            self.init_from_dict(kwargs["json"])
        elif "empty" not in kwargs or not kwargs["empty"]:
            self.init_from_dict(kwargs)

    def init_from_dict(self, source):
        if "owner" in source:
            self.owner = source["owner"]
        self.name = source["name"]
        self.tags = source["tags"]
        self.webhook = source["webhook"]
        if "blacklist" in source:
            self.blacklist = source["blacklist"]
        if "color" in source:
            self.color = source["color"]

        if "is_nsfw" in source and source["is_nsfw"]:
            self.rating = Feed.BOTH
            if "only_nsfw" in source and source["only_nsfw"]:
                self.rating = Feed.NSFW
        elif "rating" in source:
            self.rating = source["rating"]

    def dict(self):
        obj = {
            "name": self.name,
            "tags": self.tags,
            "webhook": self.webhook,
            "blacklist": self.blacklist,
            "color": self.color,
            "is_nsfw": self.rating != Feed.SFW,
            "only_nsfw": self.rating == Feed.NSFW,
        }
        if self.owner:
            obj["owner"] = self.owner
        return obj

    def json(self):
        return json.dumps(self.dict())

    def __str__(self):
        return self.json()

    def set_value(self, key, value):
        setattr(self, key, value)

