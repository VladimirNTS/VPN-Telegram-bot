import base64
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.site_router.site_views import site_router
from app.setup_logger import logger
from app.database.engine import create_db
from app.tg_bot_router.bot import start_bot, stop_bot, bot_router
from app.payment_router.payment_views import payment_router
from app.skynet_api_router.skynet_api_views import api_router
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
)
from app.utils.three_x_ui_api import ThreeXUIServer



@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db()
    await start_bot()
    yield
    await stop_bot()


app = FastAPI(lifespan=lifespan)
app.include_router(site_router, tags=['Site'])
app.include_router(bot_router, tags=['TG_BOT'])
app.include_router(payment_router, tags=['Payment'])
app.include_router(api_router, tags=['Rest API'])



@app.get("/subscription")
async def generate_subscription_config(user_token: str, session: AsyncSession = Depends(get_async_session)):
    user = await orm_get_user_by_tgid(session, int(user_token))
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
        raise HTTPException(status_code=404, detail="Не найдены сервера")
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


