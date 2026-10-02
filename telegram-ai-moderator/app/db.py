import asyncpg
from .config import settings

pool: asyncpg.Pool | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    telegram_id BIGINT PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    mode TEXT NOT NULL DEFAULT 'assist',
    max_warnings INTEGER NOT NULL DEFAULT 3,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS warnings (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    moderator_id BIGINT,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS rules (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS incidents (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    message_id BIGINT,
    category TEXT NOT NULL,
    reason TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

async def init_db():
    global pool
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    async with pool.acquire() as con:
        await con.execute(SCHEMA)
        for admin_id in settings.bootstrap_admin_ids:
            role = "owner" if admin_id == settings.owner_telegram_id else "admin"
            await con.execute(
                "INSERT INTO admins(telegram_id, role) VALUES($1,$2) ON CONFLICT (telegram_id) DO NOTHING",
                admin_id, role
            )

async def is_admin(user_id: int) -> bool:
    async with pool.acquire() as con:
        return bool(await con.fetchval("SELECT 1 FROM admins WHERE telegram_id=$1", user_id))

async def add_admin(user_id: int):
    async with pool.acquire() as con:
        await con.execute("INSERT INTO admins(telegram_id) VALUES($1) ON CONFLICT DO NOTHING", user_id)

async def remove_admin(user_id: int):
    if user_id == settings.owner_telegram_id:
        return
    async with pool.acquire() as con:
        await con.execute("DELETE FROM admins WHERE telegram_id=$1", user_id)

async def list_admins():
    async with pool.acquire() as con:
        return await con.fetch("SELECT telegram_id, role FROM admins ORDER BY role DESC, telegram_id")

async def add_warning(chat_id:int,user_id:int,moderator_id:int,reason:str)->int:
    async with pool.acquire() as con:
        await con.execute("INSERT INTO warnings(chat_id,user_id,moderator_id,reason) VALUES($1,$2,$3,$4)",chat_id,user_id,moderator_id,reason)
        return await con.fetchval("SELECT count(*) FROM warnings WHERE chat_id=$1 AND user_id=$2",chat_id,user_id)
