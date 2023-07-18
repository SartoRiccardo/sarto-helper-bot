import urllib3
import aiohttp
import aiofiles
from config import PIXABAY_API
from typing import List
import urllib.parse
import json


http = urllib3.PoolManager()


async def download_file(url, file_path):
    session = aiohttp.ClientSession()
    resp = await session.get(url)
    if resp.status == 200:
        f = await aiofiles.open(file_path, mode='wb')
        await f.write(await resp.read())
        await f.close()
    resp.close()
    await session.close()


async def pixabay_search(query: str) -> List[str]:
    result = []
    session = aiohttp.ClientSession()
    resp = await session.get("https://pixabay.com/api/?image_type=photo"
                             f"&key={PIXABAY_API}"
                             f"&q={urllib.parse.quote(query, safe='')}")
    if resp.status == 200:
        response = json.loads((await resp.read()).decode())
        for image in response["hits"]:
            if "largeImageURL" in image:
                result.append(image["largeImageURL"])

    resp.close()
    await session.close()

    return result

