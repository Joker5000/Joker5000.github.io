import hashlib
import hmac
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse
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

@app.get("/assets/{name}")
async def assets(name:str):
    if name not in {"inspector.css","inspector.js"}: return Response(status_code=404)
    return FileResponse(f"assets/{name}")

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
    <a href='/incidents'>🚨 Инциденты</a><a href='/inspector'>🎮 Режим инспектора</a><a href='/character'>✨ Character Studio</a><a href='/settings'>⚙️ Настройки</a><a href='/logout'>🚪 Выйти</a></div></div>"""
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


@app.get("/character",response_class=HTMLResponse)
async def character(request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    name=await db.get_setting("character_name","Astra")
    bio=await db.get_setting("character_bio","AI-модератор сообщества")
    style=await db.get_setting("character_style","Дружелюбный, уверенный, немного ироничный")
    emoji=await db.get_setting("character_emoji","🛡️ ✨ 👀 😂 🔥 ❤️")
    persona=await db.get_setting("persona_prompt","Ты русскоязычный AI-модератор. Общайся естественно, кратко и дружелюбно.")
    body=f"""<h1>✨ Character Studio</h1>
    <div class='panel'><h2>Образ модератора</h2><p class='muted'>Эти параметры влияют только на общение и внешний образ. На решения о наказаниях они не влияют.</p>
    <form method='post'>
    <label>Имя персонажа</label><input name='name' maxlength='64' value='{name}'>
    <label>Описание</label><input name='bio' maxlength='120' value='{bio}'>
    <label>Стиль общения</label><select name='preset'>
      <option value='friendly'>Дружелюбный</option><option value='serious'>Серьёзный</option>
      <option value='ironic'>Ироничный</option><option value='anime'>Аниме-помощник</option><option value='custom'>Свой</option>
    </select>
    <label>Описание характера</label><input name='style' value='{style}'>
    <label>Любимые emoji</label><input name='emoji' value='{emoji}'>
    <label>Подробная инструкция поведения</label><textarea name='persona'>{persona}</textarea>
    <button>💾 Сохранить персонажа</button></form></div>
    <div class='panel' style='margin-top:16px'><h2>🎭 Состояния аватара</h2>
    <div class='cards'><div class='card'>🙂 Обычный<br><span class='muted'>default</span></div>
    <div class='card'>😂 Весёлый<br><span class='muted'>fun</span></div>
    <div class='card'>⚠️ Тревога<br><span class='muted'>alert</span></div>
    <div class='card'>🌙 Ночной<br><span class='muted'>night</span></div></div>
    <p class='muted'>Автоматическое переключение Telegram-аватаров будет подключаться отдельным MTProto worker.</p></div>"""
    return HTMLResponse(layout("Character Studio",body,uid))

@app.post("/character")
async def save_character(request:Request,name:str=Form(...),bio:str=Form(...),preset:str=Form("friendly"),style:str=Form(""),emoji:str=Form(""),persona:str=Form("")):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login",303)
    presets={
      "friendly":"Дружелюбный, спокойный и поддерживающий",
      "serious":"Сдержанный, профессиональный и краткий",
      "ironic":"Уверенный, слегка ироничный, без токсичности",
      "anime":"Живой аниме-помощник, энергичный, но не навязчивый",
      "custom":style
    }
    await db.set_setting("character_name",name[:64])
    await db.set_setting("character_bio",bio[:120])
    await db.set_setting("character_style",presets.get(preset,style)[:500])
    await db.set_setting("character_emoji",emoji[:200])
    await db.set_setting("persona_prompt",persona[:2000])
    return RedirectResponse("/character",303)


INSPECTOR_STYLE="""
<style>
.inspector{background:#17140f;border:5px solid #3c3527;box-shadow:0 20px 70px #0008;padding:18px;font-family:'Courier New',monospace;position:relative;overflow:hidden}
.inspector:before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.14;background:repeating-linear-gradient(0deg,#fff0 0,#fff0 3px,#000 4px)}
.desk{display:grid;grid-template-columns:1.25fr .9fr;gap:18px}.paper{background:#d9d0a2;color:#29271f;padding:22px;min-height:510px;box-shadow:5px 7px 0 #09080655;transform:rotate(-.4deg)}
.passport{background:#d8c5b4;color:#251d1b;padding:18px;border:4px solid #4b3731;box-shadow:4px 6px 0 #0006}
.casehead{display:flex;justify-content:space-between;border-bottom:3px double #4c4939;padding-bottom:10px;margin-bottom:14px}
.messages{max-height:370px;overflow:auto;border-top:2px solid #6b664e}.msg{padding:10px 4px;border-bottom:1px dashed #777057}.msg time{font-size:11px;opacity:.65}.stampbar{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:15px}
.stamp{font-family:'Courier New',monospace;font-weight:900;font-size:18px;padding:18px 10px;border:4px solid;transform:rotate(-1deg);background:#0000}.approve{color:#3d6e2c;border-color:#3d6e2c}.warn{color:#9b2525;border-color:#9b2525}.ban{grid-column:1/-1;background:#5e1717;color:#f5c9b8;border-color:#c04736}
.stamp:hover{transform:translateY(3px) rotate(1deg);filter:brightness(1.25)}.ai-meter{height:13px;background:#3b382c;margin:7px 0}.ai-meter i{display:block;height:100%;background:#9a2e24}
.status-open{color:#d9b34a}.status-closed{color:#75a95b}
@keyframes dossierIn{from{transform:translateY(45px) rotate(-3deg);opacity:0}to{transform:translateY(0) rotate(-.4deg);opacity:1}}.paper{animation:dossierIn .45s ease-out}
@media(max-width:900px){.desk{grid-template-columns:1fr}.paper{min-height:auto}}
</style>
"""

@app.get("/inspector",response_class=HTMLResponse)
async def inspector_queue(request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    rows=await db.recent_incidents(50)
    items="".join(f"<div class='row'><div><b>ДЕЛО #{r['id']}</b> · USER {r['user_id']}<div class='muted'>{r['category']} · {r['reason']}</div></div><a class='btn' href='/case/{r['id']}/game'>🎮 НА СМЕНУ</a></div>" for r in rows if r["status"]=="open")
    body=INSPECTOR_STYLE+f"<h1>🎮 Режим инспектора</h1><p class='muted'>Очередь реальных дел Telegram-модерации.</p><div class='panel'>{items or 'Открытых дел нет. Смена спокойная.'}</div>"
    return HTMLResponse(layout("Режим инспектора",body,uid))

@app.get("/case/{incident_id}",response_class=HTMLResponse)
async def case_view(incident_id:int,request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    case=await db.get_incident(incident_id)
    if not case:return HTMLResponse(layout("Дело не найдено","<h1>Дело не найдено</h1>",uid),404)
    msgs=await db.user_messages(case["chat_id"],case["user_id"],80)
    transcript="".join(
        f"<div class='msg'><time>{x['created_at'].strftime('%d.%m %H:%M')}</time><br>{html_escape(x['text'])}</div>" for x in reversed(msgs)
    )
    score=max(0,min(100,int(case["score"]*100)))
    closed=case["status"]!="open"
    controls="" if closed else f"""<div class='stampbar'>
      <form method='post' action='/case/{incident_id}/allow'><button class='stamp approve'>✓ ПОМИЛОВАН</button></form>
      <form method='post' action='/case/{incident_id}/warn'><button class='stamp warn'>! ПРЕДУПРЕЖДЕНИЕ</button></form>
      <form method='post' action='/case/{incident_id}/ban'><button class='stamp ban'>🔫 БАН / ЗАКРЫТЬ ДОПУСК</button></form>
    </div>"""
    body=INSPECTOR_STYLE+f"""<h1>Дело #{incident_id}</h1><div class='inspector'><div class='desk'>
      <section class='paper'><div class='casehead'><b>ДОСЬЕ ПОЛЬЗОВАТЕЛЯ</b><span>#{case['user_id']}</span></div>
      <b>ЖУРНАЛ СООБЩЕНИЙ</b><div class='messages'>{transcript or 'История пуста.'}</div></section>
      <aside><div class='passport'><h2>КАРТА ДОПУСКА</h2><p>USER ID<br><b>{case['user_id']}</b></p>
      <p>ЧАТ<br><b>{case['chat_id']}</b></p><p>КАТЕГОРИЯ<br><b>{html_escape(case['category'])}</b></p>
      <p>AI УВЕРЕННОСТЬ: <b>{score}%</b></p><div class='ai-meter'><i style='width:{score}%'></i></div>
      <p>ОСНОВАНИЕ<br>{html_escape(case['reason'])}</p><p>СТАТУС: <b class='{'status-closed' if closed else 'status-open'}'>{html_escape(case['status'].upper())}</b></p></div>
      {controls}</aside></div></div>"""
    return HTMLResponse(layout(f"Дело #{incident_id}",body,uid))

def html_escape(value):
    import html
    return html.escape(str(value))

@app.post("/case/{incident_id}/{decision}")
async def case_decision(incident_id:int,decision:str,request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login",303)
    if decision not in {"allow","warn","ban"}:return RedirectResponse(f"/case/{incident_id}",303)
    case=await db.get_incident(incident_id)
    if not case or case["status"]!="open":return RedirectResponse(f"/case/{incident_id}",303)
    queued=await db.queue_case_command(incident_id,uid,decision)
    if not queued:
        return RedirectResponse(f"/case/{incident_id}",303)
    return RedirectResponse(f"/case/{incident_id}",303)


@app.get("/case/{incident_id}/photo")
async def inspector_photo(incident_id:int,request:Request):
    uid=await current_admin(request)
    if not uid:return Response(status_code=403)
    case=await db.get_incident(incident_id)
    if not case:return Response(status_code=404)
    profile=await db.get_user_profile(case["chat_id"],case["user_id"])
    if not profile or not profile["photo_file_id"]:return Response(status_code=404)
    from aiogram import Bot
    bot=Bot(settings.bot_token)
    try:
        f=await bot.get_file(profile["photo_file_id"])
        data=await bot.download_file(f.file_path)
        return Response(content=data.read(),media_type="image/jpeg",headers={"Cache-Control":"private,max-age=300"})
    finally:
        await bot.session.close()

@app.get("/case/{incident_id}/game",response_class=HTMLResponse)
async def inspector_game(incident_id:int,request:Request):
    uid=await current_admin(request)
    if not uid:return RedirectResponse("/login")
    case=await db.get_incident(incident_id)
    if not case:return HTMLResponse("Дело не найдено",404)
    p=await db.get_user_profile(case["chat_id"],case["user_id"])
    msgs=await db.user_messages(case["chat_id"],case["user_id"],120)
    warnings=await db.warning_count(case["chat_id"],case["user_id"])
    cases=await db.incident_count(case["chat_id"],case["user_id"])
    score=max(0,min(100,int(case["score"]*100)))
    name=html_escape(p["display_name"] if p else "НЕИЗВЕСТНО")
    username=html_escape(p["username"] if p else "")
    first=p["first_seen_at"].strftime("%d.%m.%Y") if p else "НЕИЗВ."
    joined=p["joined_at"].strftime("%d.%m.%Y") if p and p["joined_at"] else "НЕ ЗАФИКС."
    count=p["message_count"] if p else len(msgs)
    transcript="".join(f"<div class='msg'><b>{x['created_at'].strftime('%d.%m %H:%M')}</b><br>{html_escape(x['text'])}</div>" for x in reversed(msgs))
    photo=f"<img src='/case/{incident_id}/photo' onerror=\"this.remove();this.parentElement.innerHTML='USER'\">"
    return HTMLResponse(f"""<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><link rel='stylesheet' href='/assets/inspector.css'><body>
<div class='game'><div class='scene'><div class='statusline'>СМЕНА · ДЕЛО #{incident_id} · AI {score}%</div>
<section class='yard'><div class='fence'></div><div class='queue'><i class='person'></i><i class='person'></i><i class='person'></i><i class='person'></i><i class='person'></i><i class='person'></i></div><div class='road'></div><div class='barrier'></div><div class='booth'><div class='face'>{photo}</div></div><div class='counter'></div></section>
<section class='desk'><div class='mic'></div><div class='tray'></div><div class='weight'>51 kg</div>
<div class='stampbox'><button class='stamp red' onclick="decide({incident_id},'warn','ПРЕДУПРЕЖДЁН')">DENIED<br>ПРЕД</button><button class='stamp green' onclick="decide({incident_id},'allow','ПОМИЛОВАН')">APPROVED<br>ПРОПУСТИТЬ</button><button class='stamp gun' onclick="banConfirm({incident_id})">▰ БАН<br>АННУЛИРОВАТЬ</button></div>
<div class='doc ledger drag'><h3>СЛУЖЕБНЫЙ БЮЛЛЕТЕНЬ AI</h3><div class='checks'><span class='tag'>ЖАЛОБА</span> {html_escape(case['category']).upper()}<br><b>AI УВЕРЕННОСТЬ: {score}%</b><div class='meter'><i style='width:{score}%'></i></div><div class='ai-note'>ОСНОВАНИЕ:<br>{html_escape(case['reason'])}</div><hr>⚠ ПРЕДУПРЕЖДЕНИЙ: {warnings}<br>▣ ДЕЛ НА ПОЛЬЗОВАТЕЛЯ: {cases}<br>☑ ПРОВЕРЬТЕ ИСТОРИЮ СООБЩЕНИЙ<br>☑ СВЕРЬТЕ С ПРАВИЛАМИ ЧАТА<br><br><b>РЕШЕНИЕ ПРИНИМАЕТ АДМИНИСТРАТОР</b></div></div>
<div class='doc messages drag'><h3>ВЕДОМОСТЬ СООБЩЕНИЙ</h3><div class='scroll'>{transcript or 'Сообщений нет'}</div></div>
<div class='doc passport drag'><h2>TELEGRAM · ПРОПУСК</h2><div class='pgrid'><div class='photo'>{photo}</div><div class='fields'><b>{name}</b><br>@{username or '—'}<br>ID {case['user_id']}<hr>ВПЕРВЫЕ: {first}<br>ВХОД В ЧАТ: {joined}<br>СООБЩЕНИЙ: {count}<br>ПРЕДУПРЕЖДЕНИЙ: {warnings}<br>ДЕЛ: {cases}<br><b>СТАТУС: {html_escape(case['status']).upper()}</b></div></div></div>
<div id='verdict' class='verdict'></div></section></div></div><script src='/assets/inspector.js'></script></body></html>""")
