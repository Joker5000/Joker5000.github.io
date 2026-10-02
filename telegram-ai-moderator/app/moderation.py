import json
import re
from aiogram import Bot
from aiogram.types import Message
from openai import AsyncOpenAI
from .config import settings
from . import db
from .keyboards import punishment_menu

URL_RE=re.compile(r"https?://|t\.me/|telegram\.me/",re.I)

async def _rules_text()->str:
    rows=await db.active_rules()
    if not rows:
        return "Специальных правил пока нет. Оцени только явный спам, скам, угрозы и массовый флуд."
    return "\n".join(f"{r['id']}. {r['title']}: {r['description']}" for r in rows)

async def _cheap_signals(m:Message)->list[str]:
    text=(m.text or m.caption or "").strip()
    signals=[]
    if len(text)>1500: signals.append("очень длинное сообщение")
    if text.count("\n")>20: signals.append("много строк")
    if len(URL_RE.findall(text))>=3: signals.append("много ссылок")
    if text and len(set(text.split()))<max(2,len(text.split())//5) and len(text.split())>20:
        signals.append("сильная повторяемость текста")
    return signals

async def analyze_message(m:Message)->dict|None:
    if m.chat.type not in {"group","supergroup"} or m.from_user is None or m.from_user.is_bot:
        return None
    text=(m.text or m.caption or "").strip()
    if not text:
        return None

    mode=await db.get_setting("moderation_mode",settings.moderation_mode)
    if mode=="observe" and not settings.ai_enabled:
        return None

    signals=await _cheap_signals(m)
    if not settings.ai_enabled or not settings.openai_api_key:
        if signals:
            return {"violation":True,"category":"spam","score":0.55,"reason":", ".join(signals)}
        return None

    rules=await _rules_text()
    client=AsyncOpenAI(api_key=settings.openai_api_key,base_url=settings.openai_base_url)
    system=f"""Ты отдельный модуль модерации Telegram-группы. Не используй характер персонажа и юмор.
Оценивай только конкретное сообщение по правилам ниже. Не делай выводов о личности автора.
Правила:
{rules}

Верни ТОЛЬКО JSON:
{{"violation":true|false,"category":"spam|scam|harassment|threat|nsfw|ads|flood|rule|other","score":0.0-1.0,"reason":"краткое фактическое объяснение"}}
Если контекст неоднозначный — снижай score. Нельзя рекомендовать бан только из-за грубого тона без правила."""
    try:
        r=await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role":"system","content":system},{"role":"user","content":text[:3500]}],
            temperature=0,
            max_tokens=180,
            response_format={"type":"json_object"},
        )
        data=json.loads(r.choices[0].message.content or "{}")
        data["score"]=max(0.0,min(1.0,float(data.get("score",0))))
        return data
    except Exception:
        if signals:
            return {"violation":True,"category":"spam","score":0.5,"reason":", ".join(signals)}
        return None

async def process_moderation(bot:Bot,m:Message):
    text=(m.text or m.caption or "").strip()
    if m.from_user and not m.from_user.is_bot and text:
        await db.log_user_message(m.chat.id,m.from_user.id,m.message_id,m.from_user.username,m.from_user.full_name,text)
    result=await analyze_message(m)
    if not result or not result.get("violation"):
        return

    threshold=float(await db.get_setting("review_threshold","0.72"))
    score=float(result.get("score",0))
    if score<threshold:
        return

    category=str(result.get("category","other"))[:40]
    reason=str(result.get("reason","Подозрительное сообщение"))[:1000]
    incident_id=await db.create_incident(m.chat.id,m.from_user.id,m.message_id,category,reason,score)
    warnings=await db.user_warning_count(m.chat.id,m.from_user.id)

    username=f"@{m.from_user.username}" if m.from_user.username else m.from_user.full_name
    card=(f"🚨 <b>Инцидент #{incident_id}</b>\n"
          f"Чат: <code>{m.chat.id}</code>\n"
          f"Пользователь: {username} · <code>{m.from_user.id}</code>\n"
          f"Категория: <b>{category}</b>\n"
          f"Уверенность: <b>{score:.0%}</b>\n"
          f"Предупреждений ранее: <b>{warnings}</b>\n"
          f"Причина: {reason}\n\n"
          f"Решение принимает администратор.")

    for admin_id in await db.admin_ids():
        try:
            await bot.send_message(admin_id,card,reply_markup=punishment_menu(m.chat.id,m.from_user.id,incident_id),parse_mode="HTML")
        except Exception:
            pass
