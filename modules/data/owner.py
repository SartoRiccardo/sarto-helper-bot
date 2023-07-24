import modules.data.connection
from typing import TypedDict
postgres = modules.data.connection.postgres

Process = TypedDict("Process", {"pid": str, "pname": str})


@postgres
async def set_config(key, value, conn=None):
    await conn.execute("DELETE FROM config WHERE name = $1", key)
    await conn.execute("INSERT INTO config VALUES ($1, $2)", key, value)


@postgres
async def get_config(key, conn=None):
    if type(key) == list:
        return [(await get_config(k)) for k in key]

    data = await conn.fetch("SELECT * FROM config WHERE name = $1", key)
    if len(data) == 0:
        return None
    value = data[0]["value"]
    return value


@postgres
async def del_config(key, conn=None):
    await conn.execute("DELETE FROM config WHERE name = $1", key)


@postgres
async def get_all_config_keys(conn=None):
    return await conn.fetch("SELECT name FROM config")


@postgres
async def track_process(pid: str, pname: str, conn=None) -> None:
    await conn.execute("INSERT INTO processes (pid, pname) VALUES ($1, $2)", pid, pname)


@postgres
async def untrack_process(pid: str, conn=None) -> None:
    await conn.execute("DELETE FROM processes WHERE pid=$1", pid)


@postgres
async def get_processes(conn=None) -> list[Process]:
    return await conn.fetch("SELECT * FROM processes")
