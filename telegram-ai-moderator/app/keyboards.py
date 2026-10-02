from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Модерация", callback_data="adm:moderation"),
         InlineKeyboardButton(text="📋 Правила", callback_data="adm:rules")],
        [InlineKeyboardButton(text="👮 Администраторы", callback_data="adm:admins"),
         InlineKeyboardButton(text="🤖 ИИ", callback_data="adm:ai")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="adm:status"),
         InlineKeyboardButton(text="📜 Журнал", callback_data="adm:logs")],
    ])

def punishment_menu(chat_id:int,user_id:int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Предупредить", callback_data=f"act:warn:{chat_id}:{user_id}"),
         InlineKeyboardButton(text="🔇 Мут 24ч", callback_data=f"act:mute:{chat_id}:{user_id}")],
        [InlineKeyboardButton(text="⛔ Забанить", callback_data=f"act:ban:{chat_id}:{user_id}"),
         InlineKeyboardButton(text="✅ Оставить", callback_data=f"act:allow:{chat_id}:{user_id}")],
    ])
