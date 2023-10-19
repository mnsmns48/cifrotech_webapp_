import asyncio
import time

import asyncssh
from sshtunnel import SSHTunnelForwarder
from cfg import settings


async def connect_ssh_db():
    try:
        with SSHTunnelForwarder(
                ssh_address_or_host=settings.remote_pg_db.ssh_address_and_host,
                ssh_username=settings.remote_pg_db.ssh_username,
                ssh_password=settings.remote_pg_db.ssh_password,
                remote_bind_address=settings.remote_pg_db.ssh_bind_address
        ) as tunnel:
            tunnel.start()
            print('connect is ok')
            tunnel.stop()
    except ConnectionError:
        print('connection problem')


async def connect_asyncssh():
    async with asyncssh.connect(host=settings.remote_pg_db.ssh_address_and_host[0],
                                username=settings.remote_pg_db.ssh_username,
                                password=settings.remote_pg_db.ssh_password
                                ) as conn_asyncssh:
        if conn_asyncssh.is_client():
            print('Connected')


async def main():
    connect_task = asyncio.create_task(connect_asyncssh())
    await asyncio.gather(connect_task)


if __name__ == '__main__':
    start = time.time()
    asyncio.run(main())
    finish = time.time()
    print(finish - start)
