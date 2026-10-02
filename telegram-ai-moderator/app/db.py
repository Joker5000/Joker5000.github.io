import asyncpg
from .config import settings

pool: asyncpg.Pool | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    telegram_id BIGINT PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'admin',
    web_password_hash TEXT,
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
    chat_id BIGINT NOT NULL DEFAULT 0,
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
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE admins ADD COLUMN IF NOT EXISTS web_password_hash TEXT;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open';
"""

async def init_db():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    async with pool.acquire() as con:
        await con.execute(SCHEMA)
        for admin_id in settings.bootstrap_admin_ids:
            role = "owner" if admin_id == settings.owner_telegram_id else "admin"
            await con.execute(
                "INSERT INTO admins(telegram_id, role) VALUES($1,$2) ON CONFLICT (telegram_id) DO NOTHING",
                admin_id, role
            )

async def is_admin(user_id:int)->bool:
    async with pool.acquire() as con:
        return bool(await con.fetchval("SELECT 1 FROM admins WHERE telegram_id=$1",user_id))

async def add_admin(user_id:int):
    async with pool.acquire() as con:
        await con.execute("INSERT INTO admins(telegram_id) VALUES($1) ON CONFLICT DO NOTHING",user_id)

async def remove_admin(user_id:int):
    if user_id==settings.owner_telegram_id:return
    async with pool.acquire() as con:
        await con.execute("DELETE FROM admins WHERE telegram_id=$1",user_id)

async def list_admins():
    async with pool.acquire() as con:
        return await con.fetch("SELECT telegram_id,role,web_password_hash IS NOT NULL AS web_ready FROM admins ORDER BY role DESC,telegram_id")

async def set_web_password(user_id:int,password_hash:str):
    async with pool.acquire() as con:
        await con.execute("UPDATE admins SET web_password_hash=$2 WHERE telegram_id=$1",user_id,password_hash)

async def get_admin_auth(user_id:int):
    async with pool.acquire() as con:
        return await con.fetchrow("SELECT telegram_id,role,web_password_hash FROM admins WHERE telegram_id=$1",user_id)

async def add_warning(chat_id:int,user_id:int,moderator_id:int,reason:str)->int:
    async with pool.acquire() as con:
        await con.execute("INSERT INTO warnings(chat_id,user_id,moderator_id,reason) VALUES($1,$2,$3,$4)",chat_id,user_id,moderator_id,reason)
        return await con.fetchval("SELECT count(*) FROM warnings WHERE chat_id=$1 AND user_id=$2",chat_id,user_id)

async def dashboard_stats():
    async with pool.acquire() as con:
        return {
            "admins": await con.fetchval("SELECT count(*) FROM admins"),
            "rules": await con.fetchval("SELECT count(*) FROM rules WHERE enabled"),
            "incidents": await con.fetchval("SELECT count(*) FROM incidents"),
            "warnings": await con.fetchval("SELECT count(*) FROM warnings")
        }

async def list_rules():
    async with pool.acquire() as con:
        return await con.fetch("SELECT * FROM rules ORDER BY id DESC")

async def add_rule(title:str,description:str,created_by:int):
    async with pool.acquire() as con:
        await con.execute("INSERT INTO rules(title,description,created_by) VALUES($1,$2,$3)",title,description,created_by)

async def toggle_rule(rule_id:int):
    async with pool.acquire() as con:
        await con.execute("UPDATE rules SET enabled=NOT enabled WHERE id=$1",rule_id)

async def delete_rule(rule_id:int):
    async with pool.acquire() as con:
        await con.execute("DELETE FROM rules WHERE id=$1",rule_id)

async def recent_incidents(limit:int=100):
    async with pool.acquire() as con:
        return await con.fetch("SELECT * FROM incidents ORDER BY created_at DESC LIMIT $1",limit)

async def get_setting(key:str,default:str=""):
    async with pool.acquire() as con:
        return await con.fetchval("SELECT value FROM app_settings WHERE key=$1",key) or default

async def set_setting(key:str,value:str):
    async with pool.acquire() as con:
        await con.execute("""INSERT INTO app_settings(key,value) VALUES($1,$2)
        ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value,updated_at=now()""",key,value)


async def active_rules():
    async with pool.acquire() as con:
        return await con.fetch("SELECT id,title,description FROM rules WHERE enabled ORDER BY id")

async def admin_ids():
    async with pool.acquire() as con:
        rows=await con.fetch("SELECT telegram_id FROM admins")
        return [int(r["telegram_id"]) for r in rows]

async def create_incident(chat_id:int,user_id:int,message_id:int|None,category:str,reason:str,score:float)->int:
    async with pool.acquire() as con:
        return await con.fetchval(
            """INSERT INTO incidents(chat_id,user_id,message_id,category,reason,score)
               VALUES($1,$2,$3,$4,$5,$6) RETURNING id""",
            chat_id,user_id,message_id,category,reason,float(score)
        )

async def set_incident_status(incident_id:int,status:str):
    async with pool.acquire() as con:
        await con.execute("UPDATE incidents SET status=$2 WHERE id=$1",incident_id,status)

async def user_warning_count(chat_id:int,user_id:int)->int:
    async with pool.acquire() as con:
        return int(await con.fetchval("SELECT count(*) FROM warnings WHERE chat_id=$1 AND user_id=$2",chat_id,user_id) or 0)
