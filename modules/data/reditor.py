import os
import modules.util
import modules.data.connection
from datetime import datetime
postgres = modules.data.connection.postgres


@postgres
async def add_threads(conn, threads):
    today = datetime.now()
    values = []
    for t in threads:
        values.append(t + (today,))
    await conn.executemany(
        "INSERT INTO rdt_threads (id, title, message, msg_index, date_added) VALUES ($1, $2, $3, $4, $5)",
        values
    )


@postgres
async def get_exportable(conn):
    return await conn.fetch("SELECT * FROM rdt_videos WHERE NOT exported AND thumbnail IS NOT NULL")


@postgres
async def get_uploadable(conn):
    return await conn.fetch("SELECT * FROM rdt_videos WHERE exported AND url IS NULL")


@postgres
async def choose_threads(conn, threads):
    await conn.executemany("INSERT INTO rdt_videos(thread, message) VALUES ($1, $2)", threads)


@postgres
async def get_existing_threads(conn, threads):
    ret = await conn.fetch("SELECT id FROM rdt_threads WHERE id = ANY($1)", threads)
    ret = [r["id"] for r in ret]
    return ret


@postgres
async def get_threads(conn, message, filter=None, only_id=False):
    q = "SELECT * FROM rdt_threads WHERE message=$1"
    values = [message]
    if filter:
        q += " AND msg_index = ANY($2)"
        values.append(filter)

    ret = await conn.fetch(q, *values)
    if only_id:
        return [r["id"] for r in ret]
    return [{"id": r["id"], "title": r["title"]} for r in ret]


@postgres
async def remove_old_threads(conn):
    await conn.execute("""
        DELETE FROM rdt_threads thr
        USING rdt_videos vid
        WHERE thr.date_added < (CURRENT_DATE - 30) AND (
            (
              vid.thread = thr.id
              AND NOT (vid.exported OR vid.thumbnail IS NOT NULL)
            ) OR (
              thr.id NOT IN (SELECT thread FROM rdt_videos)
            )
        )
    """)


@postgres
async def set_video_meta(conn, message_id, title, thumbnail_url):
    await conn.execute("UPDATE rdt_videos SET title=$1, thumbnail=$2 WHERE message=$3",
                       title, thumbnail_url, message_id)


@postgres
async def discard_video(conn, thread_id=None, message_id=None):
    if message_id and not thread_id:
        results = await conn.fetch("SELECT thread FROM rdt_videos WHERE message=$1", message_id)
        if len(results) == 0:
            return False
        thread_id = results[0]["thread"]
        await conn.execute("DELETE FROM rdt_threads WHERE id=$1", thread_id)

        reditor_path = await modules.data.owner.get_config("rdt_reditor-server-path")
        if reditor_path is None:
            return True
        export_path = os.path.join(reditor_path, "exports", f"{thread_id}-export")
        if os.path.exists(export_path):
            await modules.util.logger.Logger.log(f"Deleting {export_path}", modules.util.logger.Logger.INFO)
            os.rmdir(export_path)

        return True

    return False
