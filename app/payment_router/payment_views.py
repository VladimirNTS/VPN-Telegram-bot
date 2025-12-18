from datetime import date, datetime, time
import os
import json
import hashlib
from typing import Union
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Form, HTTPException, Request 
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.tg_bot_router.kbds.inline import succes_pay_btns
from app.utils.days_to_month import days_to_str
from app.database.engine import get_async_session
from app.setup_logger import logger
from app.tg_bot_router.bot import bot
from app.database.queries import (
    orm_add_user_server,
    orm_change_user_tariff,
    orm_get_payment,
    orm_get_server,
    orm_get_servers,
    orm_get_tariff,
    orm_get_last_payment_id,
    orm_get_user,
    orm_get_user_by_tgid,
    orm_get_user_server,
    orm_get_user_server_by_ti,
    orm_get_user_servers,
    orm_new_payment,
    orm_update_user,
)
from app.utils.three_x_ui_api import ThreeXUIServer


payment_router = APIRouter(prefix="/payment")
templates = Jinja2Templates(directory='app/payment_router/templates')


@payment_router.get('/payment_page', response_class=HTMLResponse)
async def payment_page(
    request: Request,
    telegram_id: int,
    tariff_id: int, 
    session: AsyncSession = Depends(get_async_session)
):
    tariff = await orm_get_tariff(session, tariff_id=int(tariff_id))
    user = await orm_get_user_by_tgid(session, telegram_id=telegram_id)
    if not tariff or not user:
        raise HTTPException(status_code=404, detail="Tariff or User not found")
    invoice_id = await orm_get_last_payment_id(session) + 1

    receipt =  {
          "sno":"patent",
          "items": [
            {
              "name": f"подписка skynetvpn на {days_to_str(tariff.days)}",
              "quantity": 1,
              "sum": float(tariff.price),
              "payment_method": "full_payment",
              "payment_object": "service",
              "tax": "vat10"
            },
          ]
        }

    print(json.dumps(receipt, ensure_ascii=False))
    base_string = f"{os.getenv('SHOP_ID')}:{tariff.price}:{invoice_id}:{json.dumps(receipt, ensure_ascii=False)}:{os.getenv('PASSWORD_1')}"
    signature_value = hashlib.md5(base_string.encode("utf-8")).hexdigest()
    await orm_new_payment(session, tariff_id=tariff.id, user_id=user.id)

    return templates.TemplateResponse(
    "/payment_page.html", 
        {
            "request": request, 
            "price": tariff.price, 
            "time": days_to_str(tariff.days).split(' ')[0], 
            "show_time": days_to_str(tariff.days), 
            "pay_data": json.dumps(receipt, ensure_ascii=False), 
            "shop_id": os.getenv("SHOP_ID"), 
            "signature_value": signature_value, 
            "invoice_id": invoice_id
        }
    )


@payment_router.post("/get_payment")
async def choose_server(
        OutSum: Union[str, float, int] = Form(...),
        InvId: Union[str, float, int] = Form(...),
        Fee: Union[str, float, int, None] = Form(None),
        SignatureValue: str = Form(...),
        EMail: Union[str, None] = Form(None),
        PaymentMethod: Union[str, None] = Form(None),
        IncCurrLabel: Union[str, None] = Form(None),
        Shp_Receipt: Union[str, None] = Form(None),
        session: AsyncSession = Depends(get_async_session)
    ):
    payment = await orm_get_payment(session, int(InvId))
    if not payment:
        raise HTTPException(status_code=404, detail="Оплата не найдена")

    user = payment.user

    try:
        await orm_update_user(session, user.id, {'email': EMail})
    except:
        logger.error("Не удалось сменить почту пользователя")

    tariff = await orm_get_tariff(session, payment.tariff_id)
    user_servers = await orm_get_user_servers(session, user.id)
    servers = await orm_get_servers(session)
    threex_panels = []
    for i in servers:
        threex_panels.append(ThreeXUIServer(
            i.id,
            i.url,
            i.indoub_id,
            i.login,
            i.password,
            i.need_gb
        ))

    if not payment.recurent:

        if not user_servers:
            today_datetime = datetime.combine(date.today(), time.min)
            end_datetime = today_datetime + relativedelta(days=tariff.days)
            end_timestamp = int(end_datetime.timestamp() * 1000)

            for i in threex_panels:
                uuid = uuid4()
                await orm_add_user_server(
                    session, 
                    server_id=i.id,
                    tun_id = str(uuid),
                    user_id = user.id,
                )
                user_server = await orm_get_user_server_by_ti(session, str(uuid))
                server = await orm_get_server(session, user_server.server_id)
                await i.add_client(
                    uuid=str(uuid),
                    email=server.name + '_' + str(user_server.id),
                    limit_ip=tariff.ips,
                    expiry_time=end_timestamp,
                    tg_id=user.telegram_id,
                    name=user.name,
                    total_gb=tariff.trafic if i.need_gb else 0
                )
            
            await orm_change_user_tariff(
                session, 
                tariff_id=tariff.id,
                user_id=user.id,
                sub_end=end_datetime
            )

        else:
            today_datetime = datetime.combine(date.today(), time.min)
            if user.sub_end > today_datetime:
                end_datetime = user.sub_end + relativedelta(days=tariff.days)
            else:
                end_datetime = today_datetime + relativedelta(days=tariff.days)
            end_timestamp = int(end_datetime.timestamp() * 1000)

            for i in threex_panels:
                user_server = await orm_get_user_server(session, user.id, i.id)
                server = await orm_get_server(session, user_server.server_id)
                await i.edit_client(
                    uuid=user_server.tun_id,
                    email=server.name + '_' + str(user_server.id),
                    limit_ip=tariff.ips,
                    name=user.name,
                    expiry_time=end_timestamp,
                    tg_id=user.telegram_id,
                    total_gb=tariff.trafic if i.need_gb else 0
                )
            
            await orm_change_user_tariff(
                session, 
                tariff_id=tariff.id,
                user_id=user.id,
                sub_end=end_datetime
            )

        url = f"{os.getenv('URL')}/api/subscribtion?token={user.id}"
            
        await bot.send_message(
            user.telegram_id, 
            f"<b>✅ Спасибо! Вы оформили подписку!</b>\n\n🗓 Ваша подписка активна до {user.sub_end.date().strftime('%d.%m.%Y')}\n\n<b>Для автоматического подключения нажмите кнопку \"Подключиться\"\n\nДля ручного ввода скопируйте ключ. Для копирования ключа нажмите на него 1 раз. ⬇️</b>\n<code>{url}</code>",
            reply_markup=succes_pay_btns(user)
        )
        
    else:
        today_datetime = datetime.combine(date.today(), time.min)
        end_datetime = today_datetime + relativedelta(days=tariff.days)
        end_timestamp = int(end_datetime.timestamp() * 1000)

        for i in threex_panels:
            user_server = await orm_get_user_server(session, user.id, i.id)
            await i.edit_client(
                uuid=user_server.tun_id,
                email=user.name,
                limit_ip=tariff.ips,
                expiry_time=end_timestamp,
                tg_id=user.telegram_id,
                total_gb=tariff.trafic if i.need_gb else 0
            )
        
        await orm_change_user_tariff(
            session, 
            tariff_id=tariff.id,
            user_id=user.id,
            sub_end=end_datetime
        )

        url = f"{os.getenv('URL')}/api/get_sub?token={user.id}"
        await bot.send_message(user.telegram_id, f"Ваша подписка продлена до {end_datetime.strftime('%d-%m-%Y')}\nСумма списания: {tariff.price}\n\nВаш ключ для подключения: \n{url}")

    return f'OK{InvId}'



@payment_router.get("/add_servers")
async def add_user_server(user_id:int, session: AsyncSession = Depends(get_async_session)):
    user = await orm_get_user_by_tgid(session, user_id)

    user_servers = await orm_get_user_servers(session, user.id)
    servers = await orm_get_servers(session)
    threex_panels = []
    for i in servers:
        threex_panels.append(ThreeXUIServer(
            i.id,
            i.url,
            i.indoub_id,
            i.login,
            i.password,
            i.need_gb
        ))


    if not user_servers:
        end_datetime = user.sub_end
        end_timestamp = int(end_datetime.timestamp() * 1000)

        for i in threex_panels:
            uuid = uuid4()
            await orm_add_user_server(
                session, 
                server_id=i.id,
                tun_id = str(uuid),
                user_id = user.id,
            )
            user_server = await orm_get_user_server_by_ti(session, str(uuid))
            server = await orm_get_server(session, user_server.server_id)
            await i.add_client(
                uuid=str(uuid),
                email=server.name + '_' + str(user_server.id),
                limit_ip=3,
                expiry_time=end_timestamp,
                tg_id=user.telegram_id,
                name=user.name,
            )
        


