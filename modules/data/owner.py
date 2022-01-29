import modules.data.connection
postgres = modules.data.connection.postgres


@postgres
async def set_config(conn, key, value):
    await conn.execute("DELETE FROM config WHERE name = $1", key)
    await conn.execute("INSERT INTO config VALUES ($1, $2)", key, value)


@postgres
async def get_config(conn, key):
    if type(key) == list:
        return [(await get_config(k)) for k in key]

    data = await conn.fetch("SELECT * FROM config WHERE name = $1", key)
    if len(data) == 0:
        return None
    value = data[0]["value"]
    return value


@postgres
async def del_config(conn, key):
    await conn.execute("DELETE FROM config WHERE name = $1", key)


@postgres
async def get_all_config_keys(conn):
    return await conn.fetch("SELECT name FROM config")
