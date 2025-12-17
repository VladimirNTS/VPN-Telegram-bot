from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.site_router.site_views import site_router
from app.setup_logger import logger
from app.database.engine import create_db
from app.tg_bot_router.bot import start_bot, stop_bot, bot_router
from app.payment_router.payment_views import payment_router
from app.skynet_api_router.skynet_api_views import api_router


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




