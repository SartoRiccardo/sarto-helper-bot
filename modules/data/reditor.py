from modules.data.connection import postgres
from datetime import datetime


@postgres
async def add_threads(conn, threads):
    today = datetime.now()
    values = []
    for t in threads:
        values.append(t + (today,))
    await conn.executemany(
        "INSERT INTO rdt_threads (id, message, msg_index, date_added) VALUES ($1, $2, $3, $4)",
        values
    )


@postgres
async def choose_threads(conn, threads):
    threads = [(t,) for t in threads]
    await conn.executemany("INSERT INTO rdt_videos(thread) VALUES ($1)", threads)


@postgres
async def get_existing_threads(conn, threads):
    ret = await conn.fetch("SELECT id FROM rdt_threads WHERE id = ANY($1)", threads)
    ret = [r["id"] for r in ret]
    return ret


@postgres
async def get_threads(conn, message, filter=None):
    q = "SELECT * FROM rdt_threads WHERE message=$1"
    values = [message]
    if filter:
        q += " AND msg_index = ANY($2)"
        values.append(filter)

    ret = await conn.fetch(q, *values)
    return [r["id"] for r in ret]


@postgres
async def remove_old_threads(conn):
    await conn.execute("DELETE FROM rdt_threads WHERE date_added < (CURRENT_DATE - 7)")
