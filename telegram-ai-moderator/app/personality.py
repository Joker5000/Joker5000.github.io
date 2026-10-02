import asyncio
import random
import time
from aiogram import Bot
from aiogram.types import Message, ReactionTypeEmoji
from openai import AsyncOpenAI
from .config import settings
from . import db

_last_chat_reply: dict[int,float] = {}

FUN_WORDS = {
    "ахах": ["😂","🤣"],
    "лол": ["😂","🔥"],
    "кек": ["😂","😁"],
    "имба": ["🔥","👍"],
    "жесть": ["😱","🔥"],
    "база": ["👍","🔥"],
    "спасибо": ["❤️","👍"],
    "молодец": ["👏","❤️"],
}

async def _cfg(key:str, default:str)->str:
    return await db.get_setting(key, default)

async def maybe_react(bot:Bot,m:Message):
    if m.chat.type not in {"group","supergroup"} or not m.text:
        return
    if (await _cfg("social_enabled","true")).lower()!="true":
        return
    chance=float(await _cfg("reaction_chance","0.08"))
    lowered=m.text.lower()
    candidates=[]
    for word,reactions in FUN_WORDS.items():
        if word in lowered:
            candidates.extend(reactions)
    if not candidates or random.random()>chance:
        return
    try:
        emoji=random.choice(candidates)
        await bot.set_message_reaction(
            chat_id=m.chat.id,
            message_id=m.message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
            is_big=False,
        )
    except Exception:
        pass

async def maybe_chat(bot:Bot,m:Message):
    if m.chat.type not in {"group","supergroup"} or not m.text or m.from_user.is_bot:
        return
    if (await _cfg("social_enabled","true")).lower()!="true":
        return

    chance=float(await _cfg("chat_chance","0.015"))
    cooldown=int(await _cfg("chat_cooldown_sec","900"))
    now=time.time()
    if now-_last_chat_reply.get(m.chat.id,0)<cooldown:
        return

    mentioned = bot.id and (f"@{(await bot.get_me()).username}".lower() in m.text.lower())
    if not mentioned and random.random()>chance:
        return

    persona=await _cfg("persona_prompt",
        "Ты русскоязычный модератор Telegram-чата. Дружелюбный, спокойный, немного ироничный. "
        "Не провоцируй конфликты, не унижай людей, не изображай человека и не утверждай, что ты человек. "
        "Отвечай кратко, обычно 1-2 предложения. Иногда уместен лёгкий юмор."
    )

    if settings.ai_enabled and settings.openai_api_key:
        try:
            client=AsyncOpenAI(api_key=settings.openai_api_key,base_url=settings.openai_base_url)
            r=await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role":"system","content":persona},
                    {"role":"user","content":m.text[:1800]},
                ],
                temperature=0.8,
                max_tokens=120,
            )
            text=(r.choices[0].message.content or "").strip()
            if text:
                await m.reply(text[:700])
                _last_chat_reply[m.chat.id]=now
        except Exception:
            return
    elif mentioned:
        await m.reply("Я тут 👀 Если нужна модерация — тегни админа или напиши по делу.")
        _last_chat_reply[m.chat.id]=now

async def social_tick(bot:Bot,m:Message):
    await maybe_react(bot,m)
    await maybe_chat(bot,m)
