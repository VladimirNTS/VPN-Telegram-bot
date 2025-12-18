import base64
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.engine import get_async_session
from app.utils.days_to_month import days_to_str
from app.tg_bot_router.bot import bot
from app.skynet_api_router.schemas import UpdateClientGS
from app.setup_logger import logger
from app.database.queries import (
    orm_get_server,
    orm_get_servers,
    orm_get_subscribers,
    orm_get_user_by_tgid,
    orm_get_user_servers, 
    orm_get_users,
    orm_get_tariffs,
    orm_get_user,
    orm_get_admins,
    orm_update_user
)
from app.utils.three_x_ui_api import ThreeXUIServer


api_router = APIRouter(prefix='/api')


@api_router.get('/clients')
async def get_clients(session: AsyncSession = Depends(get_async_session)):
    orders = await orm_get_subscribers(session=session)

    result = []
    orders = await orm_get_users(session)
    tariffs =  await orm_get_tariffs(session)
    for order in orders:
        data = []
        tariff = 0
        for i in tariffs:
            if i.id == order.tariff_id:
                tariff = i
        if order.tariff_id > 0 or order.sub_end:
            if tariff:
                data = [order.telegram_id, order.name, order.email, order.ips, order.sub_end.strftime('%d.%m.%Y'), days_to_str(tariff.days)]
            else:
                data = [order.telegram_id, order.name, order.email, order.ips, order.sub_end.strftime('%d.%m.%Y'), "Тариф удален" if order.tariff_id else "Подписка отменена"]
            
            result.append(data)

    return result


@api_router.post("/update_client")
async def update_clients(
    data: UpdateClientGS,
    session: AsyncSession = Depends(get_async_session)
):
    now = datetime.now()
    user = await orm_get_user_by_tgid(session, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    admins = await orm_get_admins(session)
    date = data.sub_time.split('-')
    if len(date) != 3:
        for admin in admins:
            await bot.send_message(admin.telegram_id, f"Ошибка: Данные для {user.name} не обнавлены! Не верная дата!")
        raise HTTPException(status_code=404, detail="Не коректная дата!")

    user_servers = await orm_get_user_servers(session, user.id)
    servers = await orm_get_servers(session)

    new_date = datetime(int(date[0]), int(date[1]), int(date[2])+1, now.hour, now.minute, now.second, now.microsecond)
    new_unix_date = int(new_date.timestamp() * 1000)
    
    threex_panels = []
    for i in servers:
        threex_panels.append(ThreeXUIServer(
            i.id,
            i.url,
            i.indoub_id,
            i.login,
            i.password,
            False,
            i.name
        ))
    
    for server in user_servers:
        for panel in threex_panels:
            if panel.id != server.server_id:
                continue
            await panel.edit_client(
                uuid = server.tun_id, 
                name = user.name,
                email = panel.name+'_'+str(server.id), 
                limit_ip = data.devices, 
                expiry_time = new_unix_date, 
                tg_id = user.telegram_id,

            )

    await orm_update_user(
        session,
        user_id=user.id,
        data={'ips': data.devices, 'sub_end': new_date}
    )

    for admin in admins:
        await bot.send_message(admin.telegram_id, f"✅ Данные изменены для пользователя {user.name}\nДата: {new_date.strftime('%d.%m.%Y')}\nКоличество устройств: {data.devices}")


@api_router.get("/subscribtion")
async def generate_subscription_config(user_token: str, session: AsyncSession = Depends(get_async_session)):
    user = await orm_get_user(session, UUID(user_token))
    user_servers = await orm_get_user_servers(session, user.id)
    if not user or not user_servers:
        raise HTTPException(status_code=404, detail="User not found or no servers available")

    # 3. Генерируем vless:// ссылки для каждого сервера
    config_lines = []
    
    servers = await orm_get_servers(session)
    threex_panels = []
    for server in servers:
        threex_panels.append(ThreeXUIServer(
            server.id,
            server.url,
            server.indoub_id,
            server.login,
            server.password,
            server.need_gb
        ))
    for user_server in user_servers:
        vless_url = None
        for panel in threex_panels:
            if panel.id == user_server.server_id:
                vless_url = await panel.get_client_vless(user_server.tun_id)
        
        if not vless_url:
            logger.warning(f"Пользователь не найден на сервере {user_server.server_id}")
            continue
        config_lines.append(vless_url)
    
    if not config_lines:
        raise HTTPException(status_code=404)
    subscription_content = "\n".join(config_lines)

    response = Response(
        content=subscription_content,
        media_type="text/plain; charset=utf-8"
    )

    response.headers['profile-title'] = "base64:"+base64.b64encode('⚡️ SkynetVPN'.encode('utf-8')).decode('latin-1')
    response.headers["announce"] = "base64:"+base64.b64encode("🚀 Нажмите сюда, чтобы перейти в нашего бота\n\n👑 - без рекламы на YouTube\n🎧 - YouTube можно сворачивать".encode('utf-8')).decode('latin-1')
    response.headers["announce-url"] = "https://t.me/skynetaivpn_bot"
    response.headers["subscription-userinfo"] = f"expire={int(user.sub_end.timestamp())}"
    response.headers["X-Frame-Options"] = 'SAMEORIGIN'
    response.headers["Referrer-Policy"] = 'no-referrer-when-downgrade'
    response.headers["X-Content-Type-Options"] = 'nosniff'
    response.headers["Permissions-Policy"] = 'geolocation=(), microphone=()'
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"


    return response

