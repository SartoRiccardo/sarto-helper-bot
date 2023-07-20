from abc import abstractmethod, ABC
from typing import Tuple, List
import modules.data.reditor


DEBUG = 14938877
INFO = 2001125
SUCCESS = 4431943
ERROR = 12986408
WARN = 16772696


def get_short_str(video_type: str) -> str:
    if video_type == "tiktok":
        return "__*for TikTok*__"
    elif video_type == "short":
        return "__*#short*__"
    return ""


class LoggableEvent(ABC):
    @abstractmethod
    def get_log(self) -> str:
        pass

    @property
    @abstractmethod
    def severity(self) -> int:
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    async def name(self) -> str:
        return await modules.data.reditor.get_log_name(self.id)


# Debug


class LogTokensUsedGPT(LoggableEvent):
    def __init__(self, prompt: int, completion: int):
        self.prompt = prompt
        self.completion = completion

    def get_log(self) -> str:
        return f"Rough amount of prompt tokens used to generate thumbnails/titles: \n" \
               f"- Prompt: **__{self.prompt:,}__**\n" \
               f"- Completion: **__{self.completion:,}__**\n" \
               f"- Estimated Price: **__€{(self.prompt*0.0015+self.completion*0.002)/1000:.3f}__**"

    @property
    def severity(self) -> int:
        return DEBUG

    @property
    def id(self) -> str:
        return "tokens-used-gpt"


class LogThreadsGotten(LoggableEvent):
    def __init__(self, all_threads: List[str], dupes: List[str], final: List[str]):
        self.all_threads = all_threads
        self.dupes = dupes
        self.final = final

    def get_log(self) -> str:
        if len(self.all_threads) == 0:
            return "No threads found!"
        final_threads = "*None!*"
        if len(self.final) > 0:
            final_threads = "`" + "` `".join(self.final) + "`"
        return f"- All Threads: {self.all_threads}\n" + \
               (f"- Duplicate Threads: `{'` `'.join(self.dupes)}`\n"
                if len(self.dupes) > 0 else "") + \
               f"- Final Threads: {final_threads}\n"

    @property
    def severity(self) -> int:
        return DEBUG

    @property
    def id(self) -> str:
        return "thread-info"


# Info


class LogVideoDeleted(LoggableEvent):
    def __init__(self, video_name: str):
        self.video_name = video_name

    def get_log(self) -> str:
        return f"Deleted {self.video_name}."

    @property
    def severity(self) -> int:
        return INFO

    @property
    def id(self) -> str:
        return "delete-video"


# Success


# Warnings


class LogThreadAlreadyCreated(LoggableEvent):
    def __init__(self, video_name: str):
        self.video_name = video_name

    def get_log(self) -> str:
        return f"Thread for {self.video_name} already created."

    @property
    def severity(self) -> int:
        return WARN

    @property
    def id(self) -> str:
        return "thread-already-created"


# Errors
