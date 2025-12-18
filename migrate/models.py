from sqlalchemy import DateTime, func, String, BigInteger, Text, Numeric, ForeignKey, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True)
    tun_id: Mapped[str]  = mapped_column(String(50), nullable=True)
    sub_id: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[int] = mapped_column(BigInteger)
    sub_end: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    invited_by: Mapped[int] = mapped_column(BigInteger, nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    server: Mapped[int] = mapped_column(Integer(), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True) 

class Admin:
    '''Администраторы бота
    '''
    __tablename__ = 'admins'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)


class Tariff(Base):
    __tablename__ = 'tariffs'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sub_time: Mapped[int] = mapped_column(BigInteger)
    price: Mapped[int] = mapped_column(Numeric(5, 2), nullable=False)
    devices: Mapped[int] = mapped_column(Integer)
    recuring: Mapped[bool] = mapped_column(Boolean, default=False)
    

class FAQ(Base):
    __tablename__ = 'faq'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ask: Mapped[str] = mapped_column(String(50), nullable=False)
    answer: Mapped[str]  = mapped_column(Text, nullable=False)


class Payments(Base):
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    tariff_id: Mapped[int] = mapped_column(Integer)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)


class Server(Base):
    __tablename__ = 'servers'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    server_url: Mapped[str] = mapped_column(String(100))
    login: Mapped[str] = mapped_column(String(50))
    password: Mapped[str] = mapped_column(String(50))
    indoub_id: Mapped[int] = mapped_column(Integer())


class UserServer(Base):
    __tablename__ = 'users_servers'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tun_id: Mapped[str]  = mapped_column(String(50), nullable=False)
    server_id: Mapped[int] = mapped_column(ForeignKey('servers.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'), nullable=False)



