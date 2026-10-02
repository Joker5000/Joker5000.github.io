from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .config import settings

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Модерация", callback_data="adm:moderation"),
         InlineKeyboardButton(text="📋 Правила", callback_data="adm:rules")],
        [InlineKeyboardButton(text="👮 Администраторы", callback_data="adm:admins"),
         InlineKeyboardButton(text="🤖 ИИ", callback_data="adm:ai")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="adm:status"),
         InlineKeyboardButton(text="📜 Журнал", callback_data="adm:logs")],
    ])

def punishment_menu(chat_id:int,user_id:int,incident_id:int|None=None):
    rows=[
        [InlineKeyboardButton(text="🟢 ПОМИЛОВАН", callback_data=f"case:allow:{incident_id or 0}:{chat_id}:{user_id}"),
         InlineKeyboardButton(text="🔴 ПРЕДУПРЕЖДЕНИЕ", callback_data=f"case:warn:{incident_id or 0}:{chat_id}:{user_id}")],
        [InlineKeyboardButton(text="🔇 МУТ 24Ч", callback_data=f"case:mute:{incident_id or 0}:{chat_id}:{user_id}"),
         InlineKeyboardButton(text="🔫 БАН", callback_data=f"case:ban:{incident_id or 0}:{chat_id}:{user_id}")],
    ]
    if incident_id and settings.web_public_url:
        rows.append([InlineKeyboardButton(text="🎮 ОТКРЫТЬ ДЕЛО",url=f"{settings.web_public_url.rstrip('/')}/case/{incident_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
