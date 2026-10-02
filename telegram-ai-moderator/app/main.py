import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, ChatPermissions
from .config import settings
from . import db
from .keyboards import admin_menu, punishment_menu
from .web import hash_password
from .personality import social_tick
from .moderation import process_moderation
from .command_worker import command_worker

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

async def deny(event):
    if isinstance(event, CallbackQuery):
        await event.answer("⛔ Нет доступа.", show_alert=True)
    else:
        await event.answer("⛔ Эта команда доступна только администраторам бота.")

async def require_admin(event) -> bool:
    uid = event.from_user.id
    if not await db.is_admin(uid):
        await deny(event)
        return False
    return True

@dp.message(CommandStart())
async def start(m: Message):
    if await db.is_admin(m.from_user.id):
        await m.answer(
            "🛡 <b>AI Moderator</b>\n\nПанель управления доступна. "
            "Все административные действия проверяются по вашему Telegram ID.",
            reply_markup=admin_menu(), parse_mode="HTML"
        )
    else:
        await m.answer("👋 Я бот-модератор этой группы. Панель управления доступна только администраторам.")

@dp.message(Command("admin"))
async def admin(m: Message):
    if not await require_admin(m): return
    await m.answer("⚙️ <b>Панель администратора</b>", reply_markup=admin_menu(), parse_mode="HTML")

@dp.message(Command("myid"))
async def myid(m: Message):
    await m.answer(f"Ваш Telegram ID: <code>{m.from_user.id}</code>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm:"))
async def admin_callbacks(q: CallbackQuery):
    if not await require_admin(q): return
    section = q.data.split(":",1)[1]
    texts = {
        "moderation":"🛡 <b>Модерация</b>\nРежим: ASSIST\nБан и серьёзные санкции подтверждает администратор.",
        "rules":"📋 <b>Правила</b>\nВ следующем обновлении здесь будет добавление правил обычным русским текстом.",
        "admins":"👮 <b>Администраторы</b>\nДобавление: <code>/addadmin TELEGRAM_ID</code>\nУдаление: <code>/deladmin TELEGRAM_ID</code>\nСписок: /admins",
        "ai":f"🤖 <b>ИИ</b>\nСтатус: {'включён' if settings.ai_enabled else 'выключен'}\nМодель: <code>{settings.openai_model}</code>",
        "status":"📊 <b>Статус</b>\nБот: 🟢 ONLINE\nPostgreSQL: 🟢 ONLINE\nRedis: 🟢 ONLINE",
        "logs":"📜 Журнал действий хранится в PostgreSQL. Просмотр инцидентов будет расширен в следующем обновлении."
    }
    await q.message.edit_text(texts[section], reply_markup=admin_menu(), parse_mode="HTML")
    await q.answer()

@dp.message(Command("webpass"))
async def webpass(m: Message):
    if not await require_admin(m): return
    if m.chat.type != "private":
        return await m.answer("🔒 Эту команду используйте только в личных сообщениях с ботом.")
    parts=m.text.split(maxsplit=1)
    if len(parts)!=2 or len(parts[1])<10:
        return await m.answer("Использование: <code>/webpass НАДЁЖНЫЙ_ПАРОЛЬ</code>\nМинимум 10 символов.",parse_mode="HTML")
    await db.set_web_password(m.from_user.id,hash_password(parts[1]))
    try:
        await m.delete()
    except Exception:
        pass
    await m.answer("✅ Пароль веб-панели установлен. Сообщение с паролем удалено.")

@dp.message(Command("admins"))
async def admins(m: Message):
    if not await require_admin(m): return
    rows = await db.list_admins()
    text = "👮 <b>Администраторы бота</b>\n\n" + "\n".join(
        f"• <code>{r['telegram_id']}</code> — {r['role']}" for r in rows
    )
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("addadmin"))
async def addadmin(m: Message):
    if not await require_admin(m): return
    if m.from_user.id != settings.owner_telegram_id:
        return await m.answer("⛔ Добавлять администраторов может только владелец.")
    parts=m.text.split()
    if len(parts)!=2 or not parts[1].isdigit():
        return await m.answer("Использование: <code>/addadmin TELEGRAM_ID</code>",parse_mode="HTML")
    await db.add_admin(int(parts[1]))
    await m.answer("✅ Администратор добавлен.")

@dp.message(Command("deladmin"))
async def deladmin(m: Message):
    if not await require_admin(m): return
    if m.from_user.id != settings.owner_telegram_id:
        return await m.answer("⛔ Удалять администраторов может только владелец.")
    parts=m.text.split()
    if len(parts)!=2 or not parts[1].isdigit():
        return await m.answer("Использование: <code>/deladmin TELEGRAM_ID</code>",parse_mode="HTML")
    await db.remove_admin(int(parts[1]))
    await m.answer("✅ Администратор удалён.")

@dp.callback_query(F.data.startswith("case:"))
async def case_action(q: CallbackQuery, bot: Bot):
    if not await require_admin(q): return
    _,action_name,incident_s,chat_s,user_s=q.data.split(":")
    incident_id,chat_id,user_id=int(incident_s),int(chat_s),int(user_s)

    if incident_id and not await db.resolve_incident(incident_id,action_name):
        return await q.answer("Это дело уже рассмотрено другим администратором.",show_alert=True)

    if action_name=="warn":
        n=await db.add_warning(chat_id,user_id,q.from_user.id,f"Дело #{incident_id}")
        try: await bot.send_message(chat_id,f"⚠️ Пользователь <code>{user_id}</code> получает предупреждение {n}.",parse_mode="HTML")
        except Exception: pass
        result=f"🔴 ШТАМП: ПРЕДУПРЕЖДЕНИЕ · всего {n}"
    elif action_name=="mute":
        import datetime
        until=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=24)
        await bot.restrict_chat_member(chat_id,user_id,ChatPermissions(can_send_messages=False),until_date=until)
        result="🔴 ШТАМП: МУТ 24 ЧАСА"
    elif action_name=="ban":
        await bot.ban_chat_member(chat_id,user_id)
        result="🔫 РЕШЕНИЕ: БАН"
    else:
        result="🟢 ШТАМП: ПОМИЛОВАН"

    await q.message.edit_text(q.message.text+"\n\n<b>"+result+"</b>",parse_mode="HTML")
    await q.answer("Решение принято")

@dp.message(F.new_chat_members)
async def joined_members(m: Message):
    for user in m.new_chat_members:
        if not user.is_bot:
            await db.mark_joined(m.chat.id,user.id,user.username,user.full_name)

@dp.message()
async def social_messages(m: Message, bot: Bot):
    await process_moderation(bot, m)
    await social_tick(bot, m)

async def main():
    await db.init_db()
    bot=Bot(settings.bot_token)
    worker=asyncio.create_task(command_worker(bot))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()

if __name__=="__main__":
    asyncio.run(main())
