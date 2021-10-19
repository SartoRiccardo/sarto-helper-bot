import asyncpg
import config

connection = None


async def start():
    global connection
    connection = await asyncpg.create_pool(
        user=config.DB_USER, password=config.DB_PASSWORD,
        database=config.DB_NAME, host=config.DB_HOST
    )


def postgres(func):
    async def inner(*args, **kwargs):
        if connection is None:
            return
        return await func(connection, *args, **kwargs)
    return inner


