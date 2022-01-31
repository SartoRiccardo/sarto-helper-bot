import urllib3
import aiohttp
import aiofiles
import os


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
