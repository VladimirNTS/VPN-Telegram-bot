from typing import Union

from sqlalchemy import select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from migrate.models import (
    Tariff, 
    User, 
    Admin, 
    FAQ, 
    Payments, 
    Server,
    UserServer,
)


async def orm_change_user_status(session_pool: AsyncSession, user_id, new_status, sub_end, tun_ids = None):
    async with session_pool() as session:
        
        query = update(User).where(User.id == int(user_id)).values(
                status=new_status,
                sub_end=sub_end,
            )

        await session.execute(query)
        
        query = select(UserServer).where(UserServer.user_id == int(user_id))
        servers_list = await session.execute(query)
        servers_list = servers_list.scalars().all()
        
        if not servers_list and tun_ids:
            for server_id, tun_id in tun_ids.items():
                await orm_add_user_server(session_pool, int(user_id), int(server_id), str(tun_id))

        await session.commit()


async def orm_update_email(session_pool: AsyncSession, user_id, email):
    async with session_pool() as session:
        
        query = update(User).where(User.id == int(user_id)).values(
                email=str(email),
            )

        await session.execute(query)
        
        await session.commit()





async def orm_add_user_server(session_pool, user_id, server_id, tun_id):
    async with session_pool() as session:
        obj = UserServer(
            server_id=server_id,
            user_id=user_id,
            tun_id=tun_id,
        )
        session.add(obj)
        await session.commit()


async def orm_delete_user_server(session_pool, tun_id):
    async with session_pool() as session:
        query = delete(UserServer).where(UserServer.tun_id == tun_id)
        await session.execute(query)
        await session.commit()


async def old_orm_get_user_servers(session_pool, user_id):
    async with session_pool() as session:
        query = select(UserServer).where(UserServer.user_id == user_id)
        result = await session.execute(query)

        return result.scalars().all()


async def orm_get_user_servers_by_si(session_pool, server_id):
    async with session_pool() as session:
        query = select(UserServer).where(UserServer.server_id == server_id)
        result = await session.execute(query)

        return result.scalars().all()


async def orm_change_user_server(session_pool: AsyncSession, user_id, server):
    async with session_pool() as session:
        
        query = update(User).where(User.id == user_id).values(
                server=int(server)
            )
        await session.execute(query)
        await session.commit()





async def old_orm_get_users(session_pool: AsyncSession):
    '''Возвращает список пользвателей
    
    session: Ассинхроная сессия sqlalchemy
    '''
    async with session_pool() as session:
        query = select(User)
        result = await session.execute(query)
        return result.scalars().all()


async def orm_get_subscribers(session_pool: AsyncSession):
    '''Возвращает список пользвателей
    
    session: Ассинхроная сессия sqlalchemy
    '''
    async with session_pool() as session:
        query = select(User).where(User.status != 0)
        result = await session.execute(query)
        return result.scalars().all()


async def orm_get_blocked_users(session_pool: AsyncSession):
    '''Возвращает список пользвателей
    
    session: Ассинхроная сессия sqlalchemy
    '''
    async with session_pool() as session:
        query = select(User).where(User.blocked == True)
        result = await session.execute(query)
        return result.scalars().all()


async def orm_get_user(session_pool: AsyncSession, user_id: int):
    async with session_pool() as session:
        query = select(User).where(User.user_id == user_id)
        result = await session.execute(query)
        return result.scalar()


async def orm_get_user_by_id(session_pool: AsyncSession, user_id: int):
    async with session_pool() as session:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        return result.scalar()


async def orm_block_user(session_pool: AsyncSession, user_id: int):
    '''Блокирует пользователя'''
    async with session_pool() as session:
        query = update(User).where(User.id == user_id).values(blocked=True)
        await session.execute(query)
        await session.commit()


async def orm_unblock_user(session_pool: AsyncSession, user_id: int):
    '''Блокирует пользователя'''
    async with session_pool() as session:
        query = update(User).where(User.id == user_id).values(blocked=False)
        await session.execute(query)
        await session.commit()


# Работа с администраторами
async def orm_add_admin(session_pool, user_id):
    '''Добавить нового администратора в таблицу'''
    async with session_pool() as session:
        session.add(
            Admin(
                user_id=user_id
            )
        )
        await session.commit()


async def orm_delete_admin(session_pool, user_id):
    '''Удалить администратора из таблицы'''
    async with session_pool() as session:
        query = delete(Admin).where(user_id==user_id)
        await session.execute(query)
        await session.commit()


# FAQ
async def orm_get_faq(session_pool: AsyncSession):
    '''Возвращает список вопросов и ответов'''
    async with session_pool() as session:
        query = select(FAQ)
        result = await session.execute(query)
        return result.scalars().all()


async def orm_add_faq(session_pool: AsyncSession, data: dict):
    '''Добавляет вопрос и ответ в таблицу'''
    async with session_pool() as session:
        obj = FAQ(
            ask=data["ask"],
            answer=data["answer"],
        )
        session.add(obj)
        await session.commit()


async def orm_get_faq_by_id(session_pool: AsyncSession, id: int):
    '''Возвращает вопрос и ответ по id'''
    async with session_pool() as session:
        query = select(FAQ).where(FAQ.id == id)
        result = await session.execute(query)
        return result.scalar()


async def orm_delete_faq(session_pool: AsyncSession, id: int):
    '''Удалить вопрос из таблицы'''
    async with session_pool() as session:
        query = delete(FAQ).where(FAQ.id == id)
        await session.execute(query)
        await session.commit()


async def orm_edit_faq(session_pool: AsyncSession, id: int, fields: dict):
    '''Обновляет только переданные поля вопроса и ответа по id.
    fields: dict - только те поля, которые нужно обновить (например: {'ask': '...', 'answer': '...'})
    '''
    async with session_pool() as session:
        if not fields:
            return
        query = update(FAQ).where(FAQ.id == id).values(**fields)
        await session.execute(query)
        await session.commit()


async def orm_end_payment(session_pool: AsyncSession, id: int):
    async with session_pool() as session:
        query = update(Payments).where(Payments.id == id).values(paid = True)
        await session.execute(query)
        await session.commit()

async def get_user_last_payment(session_pool, user_id):
    async with session_pool() as session:
        query = select(Payments).where(Payments.user_id == user_id).where(Payments.paid == True).order_by(Payments.id.desc()).limit(1)
        result = await session.execute(query)
        payment = result.scalar_one_or_none()
        
        return payment.id if payment else 0




async def orm_new_payment(session_pool: AsyncSession, user_id: int, tariff_id: int):
    '''Создает новую запись о платеже в таблицу'''
    async with session_pool() as session:
        obj = Payments(
            user_id=user_id,
            tariff_id=tariff_id,
        )
        session.add(obj)
        await session.commit()


async def orm_get_payment(session_pool: AsyncSession, payment_id):
    '''Возвращает запись о платеже по id'''
    async with session_pool() as session:
        query = select(Payments).where(Payments.id == payment_id)
        result = await session.execute(query)
        return result.scalar()


async def orm_get_last_payment_id(session_pool: AsyncSession):
    '''Возвращает последнюю запись о платеже'''
    async with session_pool() as session:
        query = select(Payments).order_by(Payments.id.desc()).limit(1)
        result = await session.execute(query)
        payment = result.scalar_one_or_none()
        
        return payment.id if payment else 0


async def orm_add_server(session_pool: AsyncSession, data):
    async with session_pool() as session:
        obj = Server(
            name=data['name'],
            server_url=data['url'],
            login=data['login'],
            password=data['password'],
            indoub_id=data['indoub_id']
        )
        session.add(obj)
        await session.commit()
        query = select(Server).where(Server.server_url == data['url']).where(Server.indoub_id == int(data['indoub_id']))
        result = await session.execute(query)
        return result.scalar()



async def orm_delete_server(session_pool, id):
    async with session_pool() as session:
        query = delete(Server).where(Server.id == id)
        await session.execute(query)
        await session.commit()


async def orm_edit_server(session_pool, id: int, fields: dict):
    async with session_pool() as session:
        if not fields:
            return
        query = update(Server).where(Server.id == id).values(**fields)
        await session.execute(query)
        await session.commit()


async def orm_get_servers(session_pool):
    async with session_pool() as session:
        query = select(Server)
        result = await session.execute(query)
        return result.scalars().all() 


async def orm_get_server(session_pool, id):
    async with session_pool() as session:
        query = select(Server).where(Server.id == id)
        result = await session.execute(query)
        return result.scalar()


