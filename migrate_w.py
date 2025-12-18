import asyncio

from migrate.queries import old_orm_get_users, old_orm_get_user_servers
from migrate.engine import old_session
from app.database.engine import async_session_maker
from app.setup_logger import logger
from app.database.queries import (
    orm_add_user,
    orm_get_user_by_tgid,
    orm_add_user_server,
    orm_change_user_tariff,
    orm_update_user
)
from app.database.models import UserServer

sync_servers = {
    5: 3,
    6: 2,
    8: 4,
    7: 1,
    70: 6,
    68: 5
}


sync_tariff = {
    1: 2,
    2: 3,
    3: 4,
    4: 1
}


async def emails():

    old_users = await old_orm_get_users(old_session)
    async with async_session_maker() as session:
        for i in old_users:
            await orm_update_user(session, i.user_id, {'email': i.email})



async def migrate():
    old_users = await old_orm_get_users(old_session)


    async with async_session_maker() as session:
        for old_user in old_users:
            old_users_servers = await old_orm_get_user_servers(old_session, old_user.id)
            
            await orm_add_user(
                session,
                name=old_user.name,
                telegram_id=old_user.user_id,
                invited_by=old_user.invited_by
            )
            new_user = await orm_get_user_by_tgid(session, old_user.user_id)
            if not old_users_servers:
                continue
            tun_ids = {}
            for old_user_server in old_users_servers:
                if not sync_servers.get(int(old_user_server.server_id)):
                    continue
                logger.info("Пользователь добавлен {new_user.id}")
                session.add(UserServer(
                    user_id=new_user.id,
                    server_id=sync_servers.get(old_user_server.server_id),
                    tun_id=old_user_server.tun_id
                ))
                await session.commit()

            await orm_change_user_tariff(
                session,
                new_user.id,
                sync_tariff.get(old_user.status, 0),
                old_user.sub_end,
            )



if __name__ == "__main__":
    asyncio.run(emails())



