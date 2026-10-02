import asyncio
import datetime
from aiogram import Bot
from aiogram.types import ChatPermissions
from . import db

async def command_worker(bot:Bot):
    while True:
        try:
            commands=await db.pending_commands()
            for cmd in commands:
                error=None
                action=cmd["action"]
                try:
                    if action=="warn":
                        await db.add_warning(cmd["chat_id"],cmd["user_id"],cmd["admin_id"],f"Дело #{cmd['incident_id']}")
                        try:
                            await bot.send_message(cmd["chat_id"],f"⚠️ Пользователь <code>{cmd['user_id']}</code> получает предупреждение.",parse_mode="HTML")
                        except Exception:
                            pass
                    elif action=="mute":
                        until=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=24)
                        permissions=ChatPermissions(can_send_messages=False)
                        await bot.restrict_chat_member(cmd["chat_id"],cmd["user_id"],permissions,until_date=until)
                    elif action=="ban":
                        await bot.ban_chat_member(cmd["chat_id"],cmd["user_id"])
                    elif action!="allow":
                        raise ValueError("unknown action")
                except Exception as exc:
                    error=str(exc)[:500]
                await db.finish_command(cmd["id"],cmd["incident_id"],action,error)
        except Exception:
            pass
        await asyncio.sleep(1.5)
