import os
import shutil
import modules.util
import modules.data.connection
from datetime import datetime
postgres = modules.data.connection.postgres


@postgres
async def add_threads(threads, conn=None):
    today = datetime.now()
    values = []
    for t in threads:
        values.append(t + (today,))
    await conn.executemany(
        "INSERT INTO rdt_threads (id, title, message, msg_index, date_added) VALUES ($1, $2, $3, $4, $5)",
        values
    )


@postgres
async def get_exportable(shorts=False, conn=None):
    return await conn.fetch(f"""
        SELECT *
        FROM rdt_videos
        WHERE NOT exported
          AND thumbnail IS NOT NULL
          AND {"" if shorts else "NOT"} is_short
    """)


@postgres
async def get_uploadable(shorts=False, conn=None):
    return await conn.fetch(f"""
        SELECT *
        FROM rdt_videos
        WHERE exported
          AND url IS NULL
          AND {"" if shorts else "NOT"} is_short
    """)


@postgres
async def choose_threads(threads, conn=None):
    await conn.executemany("INSERT INTO rdt_videos(thread, message) VALUES ($1, $2)", threads)


@postgres
async def get_existing_threads(threads, conn=None):
    ret = await conn.fetch("SELECT id FROM rdt_threads WHERE id = ANY($1)", threads)
    ret = [r["id"] for r in ret]
    return ret


@postgres
async def get_threads(message, filter=None, only_id=False, conn=None):
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
async def remove_old_threads(conn=None):
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
async def set_video_meta(message_id, title, thumbnail_url, is_short=False, conn=None):
    await conn.execute("UPDATE rdt_videos SET title=$1, thumbnail=$2, is_short=$4 WHERE message=$3",
                       title, thumbnail_url, message_id, is_short)


@postgres
async def discard_video(thread_id=None, message_id=None, conn=None):
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
            await modules.util.logger.Logger.log(modules.util.log_events.LogVideoDeleted(export_path))
            shutil.rmtree(export_path)

        return True

    return False


@postgres
async def get_newly_created_videos(conn=None):
    """
    Gets created (but not exported) document IDs that don't have a thread open.
    """
    results = await conn.fetch("""
    SELECT document_id
    FROM rdt_videos
    WHERE document_id IS NOT NULL
      AND thread NOT IN (SELECT thread FROM rdt_create_channel)
      AND NOT exported
    """)
    return [r["document_id"] for r in results]


@postgres
async def get_document_info(document_id, conn=None):
    result = await conn.fetch("""
        SELECT *
        FROM rdt_videos
        WHERE document_id=$1
          AND NOT exported
    """, document_id)
    if len(result) == 0:
        return None
    return result[0]


@postgres
async def set_video_thread(thread_id, discord_thread_id, conn=None):
    await conn.execute("""
    INSERT INTO rdt_create_channel (thread, channel_id) VALUES ($1, $2)
    """, thread_id, discord_thread_id)


@postgres
async def set_video_scenes(channel_id, messages, scene_ids, conn=None):
    values = []
    for i in range(min(len(messages), len(scene_ids))):
        values.append((channel_id, messages[i], scene_ids[i]))
    await conn.executemany("""
    INSERT INTO rdt_create_messages (channel_id, message, scene_id) VALUES ($1, $2, $3)
    """, values)


@postgres
async def get_scene_info(thread_id: int, message_id: int, conn=None):
    """Gets the ID of a scene that is bound to a message in a thread."""
    result = await conn.fetch("""
        SELECT vid.document_id, msg.scene_id
        FROM rdt_create_messages AS msg
            JOIN rdt_create_channel AS chnl
                ON chnl.channel_id = msg.channel_id
            JOIN rdt_videos AS vid
                ON vid.thread = chnl.thread
        WHERE msg.channel_id=$1 AND msg.message=$2
    """, thread_id, message_id)
    if len(result) == 0:
        return None
    return [result[0]["document_id"], result[0]["scene_id"]]


@postgres
async def get_newly_exported_documents(conn=None):
    result = await conn.fetch("""
        SELECT v.document_id
        FROM rdt_create_channel AS cc
            JOIN rdt_videos AS v
                ON cc.thread = v.thread
        WHERE v.exported
    """)
    return [r["document_id"] for r in result]


@postgres
async def get_thread_id(document_id, conn=None):
    result = await conn.fetch("""
        SELECT channel_id
        FROM rdt_create_channel AS cc
            JOIN rdt_videos AS v
                ON cc.thread = v.thread
        WHERE v.document_id = $1
    """, document_id)
    if len(result) == 0:
        return None
    return result[0]["channel_id"]


@postgres
async def delete_thread(thread_id, conn=None):
    await conn.execute("""
        DELETE FROM rdt_create_messages
        WHERE channel_id=$1
    """, thread_id)
    await conn.execute("""
        DELETE FROM rdt_create_channel
        WHERE channel_id=$1
    """, thread_id)


@postgres
async def get_video_info(thread, conn=None):
    results = await conn.fetch("""
        SELECT * FROM rdt_videos WHERE thread=$1
    """, thread)
    if len(results) == 0:
        return None
    return results[0]


@postgres
async def get_logging_status(conn=None):
    results = await conn.fetch("SELECT * FROM rdt_logging")
    return results


@postgres
async def set_logging_status(log: str, status: bool, conn=None):
    await conn.execute("UPDATE rdt_logging SET active=$2 WHERE log_id=$1", log, status)


@postgres
async def is_log_active(log: str, conn=None) -> bool:
    results = await conn.fetch("SELECT active FROM rdt_logging where log_id=$1", log)
    return results[0]["active"] if len(results) > 0 else False


@postgres
async def get_log_name(log: str, conn=None) -> str:
    results = await conn.fetch("SELECT name FROM rdt_logging where log_id=$1", log)
    return results[0]["name"] if len(results) > 0 else log
