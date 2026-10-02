import hashlib
import hmac
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from .config import settings
from . import db

def hash_password(password:str)->str:
    salt=os.urandom(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,310000)
    return f"{salt.hex()}:{digest.hex()}"

def verify_password(password:str,stored:str)->bool:
    try:
        salt_hex,digest_hex=stored.split(":",1)
        actual=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),310000).hex()
        return hmac.compare_digest(actual,digest_hex)
    except Exception:
        return False

@asynccontextmanager
async def lifespan(app:FastAPI):
    await db.init_db()
    yield

app=FastAPI(title="Telegram AI Moderator",lifespan=lifespan)
app.add_middleware(SessionMiddleware,secret_key=settings.web_session_secret,https_only=False,same_site="lax")

STYLE="""
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;background:#0b1020;color:#e8ecf4}
.shell{display:flex;min-height:100vh}.side{width:250px;background:#11182b;padding:28px 18px;border-right:1px solid #26304a}
.logo{font-size:21px;font-weight:800;margin-bottom:28px}.logo span{color:#5da9ff}.nav a{display:block;color:#aebbd0;text-decoration:none;padding:12px 14px;border-radius:10px;margin:5px 0}.nav a:hover{background:#1c2741;color:white}
.main{flex:1;padding:34px;max-width:1200px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card,.panel{background:#131c31;border:1px solid #26324d;border-radius:16px;padding:20px}.num{font-size:30px;font-weight:800;margin-top:8px}
h1{margin-top:0}input,textarea,select{width:100%;padding:11px;background:#0c1426;color:white;border:1px solid #34415f;border-radius:9px;margin:6px 0 12px}button,.btn{background:#2878e8;color:white;border:0;border-radius:9px;padding:10px 15px;cursor:pointer;text-decoration:none;display:inline-block}.danger{background:#b83a4b}.muted{color:#8998b1}.row{display:flex;gap:12px;align-items:center;justify-content:space-between;border-bottom:1px solid #27324b;padding:12px 0}.ok{color:#66d19e}.off{color:#ff8794}
.login{max-width:430px;margin:12vh auto}.badge{background:#223354;padding:4px 9px;border-radius:20px;font-size:12px}
@media(max-width:800px){.side{display:none}.main{padding:18px}.cards{grid-template-columns:1fr 1fr}}
</style>
"""

def layout(title:str,body:str,user_id:int|None=None)->str:
    if user_id is None:return f"<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>{title}</title>{STYLE}<body>{body}</body></html>"
    nav="""<div class='side'><div class='logo'>🛡 <span>AI</span> Moderator</div><div class='nav'>
    <a href='/'>📊 Обзор</a><a href='/rules'>📋 Правила</a><a href='/admins'>👮 Администраторы</a>
    <a href='/incidents'>🚨 Инциденты</a><a href='/settings'>⚙️ Настройки</a><a href='/logout'>🚪 Выйти</a></div></div>"""
    return f"<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>{title}</title>{STYLE}<body><div class='shell'>{nav}<main class='main'>{body}</main></div></body></html>"

async def current_admin(request:Request):
    uid=request.session.get("uid")
    if not uid:return None
    if not await db.is_admin(int(uid)):
        request.session.clear();return None
    return int(uid)

@app.get("/login",response_class=HTMLResponse)
async def login_page(request:Request,error:str=""):
    body=f"""<div class='login panel'><h1>🛡 AI Moderator</h1><p class='muted'>Закрытая панель администратора</p>
    {'<p class="off">Неверный Telegram ID или пароль.</p>' if error else ''}
    <form method='post'><label>Telegram ID</label><input name='telegram_id' inputmode='numeric' required>
    <label>Пароль панели</label><input name='password' type='password' required>
    <button>Войти</button></form><p class='muted'>Пароль задаётся в личке боту командой /webpass.</p></div>"""
    return HTMLResponse(layout("Вход",body))

@app.post("/login")
async def login(request:Request,telegram_id:int=Form(...),password:str=Form(...)):
    row=await db.get_admin_auth(telegram_id)
    if not row or not row["web_password_hash"] or not verify_password(password,row["web_password_hash"]):
        return RedirectResponse("/login?error=1",303)
    request.session["uid"]=telegram_id
    return RedirectResponse("/",303)

@app.get("/logout")
async def logout(request:Request):
    request.session.clear();return RedirectResponse("/login",303)

@app.get("/",response_class=HTMLResponse)
async def dashboard(request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    s=await db.dashboard_stats()
    body=f"""<h1>Панель управления</h1><p class='muted'>Вход выполнен как Telegram ID {uid}</p>
    <div class='cards'><div class='card'>Администраторы<div class='num'>{s['admins']}</div></div>
    <div class='card'>Активные правила<div class='num'>{s['rules']}</div></div>
    <div class='card'>Инциденты<div class='num'>{s['incidents']}</div></div>
    <div class='card'>Предупреждения<div class='num'>{s['warnings']}</div></div></div>
    <div class='panel' style='margin-top:16px'><h2>Состояние</h2><p>Бот <span class='ok'>● работает</span></p><p>PostgreSQL <span class='ok'>● подключён</span></p><p>Режим модерации <span class='badge'>ASSIST</span></p></div>"""
    return HTMLResponse(layout("Обзор",body,uid))

@app.get("/rules",response_class=HTMLResponse)
async def rules(request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    rows=await db.list_rules()
    items="".join(f"""<div class='row'><div><b>{r['title']}</b><div class='muted'>{r['description']}</div></div>
    <div><span class='badge'>{'ВКЛ' if r['enabled'] else 'ВЫКЛ'}</span> <form style='display:inline' method='post' action='/rules/{r['id']}/toggle'><button>Переключить</button></form>
    <form style='display:inline' method='post' action='/rules/{r['id']}/delete'><button class='danger'>Удалить</button></form></div></div>""" for r in rows)
    body=f"""<h1>📋 Правила</h1><div class='panel'><h2>Добавить правило</h2><form method='post' action='/rules'>
    <input name='title' placeholder='Название, например: Запрет рекламы' required>
    <textarea name='description' placeholder='Опишите правило обычным русским языком' required></textarea><button>Добавить</button></form></div>
    <div class='panel' style='margin-top:16px'>{items or '<p class="muted">Правил пока нет.</p>'}</div>"""
    return HTMLResponse(layout("Правила",body,uid))

@app.post("/rules")
async def add_rule(request:Request,title:str=Form(...),description:str=Form(...)):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login",303)
    await db.add_rule(title[:120],description[:3000],uid);return RedirectResponse("/rules",303)

@app.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id:int,request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login",303)
    await db.toggle_rule(rule_id);return RedirectResponse("/rules",303)

@app.post("/rules/{rule_id}/delete")
async def delete_rule(rule_id:int,request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login",303)
    await db.delete_rule(rule_id);return RedirectResponse("/rules",303)

@app.get("/admins",response_class=HTMLResponse)
async def admins(request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    rows=await db.list_admins()
    items="".join(f"<div class='row'><b>{r['telegram_id']}</b><span>{r['role']} · {'web ✓' if r['web_ready'] else 'web —'}</span></div>" for r in rows)
    return HTMLResponse(layout("Администраторы",f"<h1>👮 Администраторы</h1><div class='panel'>{items}</div><p class='muted'>Добавление и удаление администраторов выполняет владелец через Telegram.</p>",uid))

@app.get("/incidents",response_class=HTMLResponse)
async def incidents(request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    rows=await db.recent_incidents()
    items="".join(f"<div class='row'><div><b>{r['category']}</b> · user {r['user_id']}<div class='muted'>{r['reason']}</div></div><span class='badge'>{r['score']:.0%}</span></div>" for r in rows)
    return HTMLResponse(layout("Инциденты",f"<h1>🚨 Инциденты</h1><div class='panel'>{items or '<p class=muted>Инцидентов пока нет.</p>'}</div>",uid))

@app.get("/settings",response_class=HTMLResponse)
async def settings_page(request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    mode=await db.get_setting("moderation_mode",settings.moderation_mode)
    social=await db.get_setting("social_enabled","true")
    reaction=await db.get_setting("reaction_chance","0.08")
    chat=await db.get_setting("chat_chance","0.015")
    cooldown=await db.get_setting("chat_cooldown_sec","900")
    persona=await db.get_setting("persona_prompt","Дружелюбный, спокойный русскоязычный AI-модератор с лёгкой иронией.")
    body=f"""<h1>⚙️ Настройки</h1><div class='panel'><form method='post'>
    <label>Режим модерации</label><select name='mode'><option value='observe' {'selected' if mode=='observe' else ''}>Наблюдение</option>
    <option value='assist' {'selected' if mode=='assist' else ''}>Помощник (рекомендуется)</option>
    <option value='automatic' {'selected' if mode=='automatic' else ''}>Автоматический</option></select>
    <h2>💬 Характер и общение</h2>
    <label>Социальный режим</label><select name='social'><option value='true' {'selected' if social=='true' else ''}>Включён</option><option value='false' {'selected' if social=='false' else ''}>Выключен</option></select>
    <label>Вероятность реакции (0–1)</label><input name='reaction' value='{reaction}'>
    <label>Вероятность случайной реплики (0–1)</label><input name='chat' value='{chat}'>
    <label>Минимальный интервал между репликами, секунд</label><input name='cooldown' value='{cooldown}'>
    <label>Характер персонажа</label><textarea name='persona'>{persona}</textarea>
    <button>Сохранить</button></form></div>"""
    return HTMLResponse(layout("Настройки",body,uid))

@app.post("/settings")
async def save_settings(request:Request,mode:str=Form(...),social:str=Form("true"),reaction:str=Form("0.08"),chat:str=Form("0.015"),cooldown:str=Form("900"),persona:str=Form("")):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login",303)
    if mode not in {"observe","assist","automatic"}:mode="assist"
    await db.set_setting("moderation_mode",mode)
    await db.set_setting("social_enabled","true" if social=="true" else "false")
    try: reaction=str(max(0.0,min(1.0,float(reaction))))
    except: reaction="0.08"
    try: chat=str(max(0.0,min(0.25,float(chat))))
    except: chat="0.015"
    try: cooldown=str(max(60,int(cooldown)))
    except: cooldown="900"
    await db.set_setting("reaction_chance",reaction)
    await db.set_setting("chat_chance",chat)
    await db.set_setting("chat_cooldown_sec",cooldown)
    await db.set_setting("persona_prompt",persona[:2000])
    return RedirectResponse("/settings",303)
