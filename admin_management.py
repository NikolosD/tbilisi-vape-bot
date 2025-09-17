# ============== УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ ==============

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from config import ADMIN_IDS, SUPER_ADMIN_ID
from keyboards import get_admin_management_keyboard, get_admins_list_keyboard

router = Router()

class AdminManagementStates(StatesGroup):
    waiting_admin_id = State()

@router.callback_query(F.data == "manage_admins")
async def manage_admins(callback: CallbackQuery):
    """Меню управления администраторами (только для супер-админа)"""
    if callback.from_user.id != SUPER_ADMIN_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"👥 <b>Управление администраторами</b>\n\n"
        f"Выберите действие:",
        reply_markup=get_admin_management_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления админа"""
    if callback.from_user.id != SUPER_ADMIN_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    await state.set_state(AdminManagementStates.waiting_admin_id)
    await callback.message.edit_text(
        "➕ <b>Добавление администратора</b>\n\n"
        "Отправьте ID пользователя или перешлите его сообщение.\n\n"
        "💡 <i>Пользователь может узнать свой ID у бота @userinfobot</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="manage_admins")]
        ]),
        parse_mode='HTML'
    )

@router.message(AdminManagementStates.waiting_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    """Обработать ID нового админа"""
    print(f"DEBUG: process_admin_id called, user_id={message.from_user.id}, text={message.text}")
    print(f"DEBUG: SUPER_ADMIN_ID={SUPER_ADMIN_ID}")
    
    if message.from_user.id != SUPER_ADMIN_ID:
        print(f"DEBUG: Not super admin, deleting message")
        await message.delete()
        return
    
    print(f"DEBUG: Processing admin ID...")
    
    # Проверяем, переслано ли сообщение
    if message.forward_from:
        new_admin_id = message.forward_from.id
        username = message.forward_from.username
        first_name = message.forward_from.first_name
    else:
        # Пытаемся получить ID из текста
        try:
            new_admin_id = int(message.text.strip())
            # Пытаемся получить информацию о пользователе
            try:
                chat = await message.bot.get_chat(new_admin_id)
                username = chat.username
                first_name = chat.first_name
            except:
                username = None
                first_name = f"User {new_admin_id}"
        except ValueError:
            await message.answer(
                "❌ Неверный формат ID. Отправьте числовой ID или перешлите сообщение пользователя.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="add_admin")],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="manage_admins")]
                ])
            )
            return
    
    # Проверяем, не является ли пользователь уже админом
    if new_admin_id in ADMIN_IDS or await db.is_admin_in_db(new_admin_id):
        await message.answer(
            f"⚠️ Пользователь {first_name} уже является администратором.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_admins")]
            ])
        )
        await state.clear()
        return
    
    # Добавляем админа в базу данных
    await db.add_admin(new_admin_id, username, first_name, message.from_user.id)
    
    # Добавляем в список ADMIN_IDS
    if new_admin_id not in ADMIN_IDS:
        ADMIN_IDS.append(new_admin_id)
    
    await message.answer(
        f"✅ <b>Администратор добавлен</b>\n\n"
        f"👤 Имя: {first_name}\n"
        f"🆔 ID: {new_admin_id}\n"
        f"📱 Username: @{username if username else 'Нет'}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_admin")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_admins")]
        ]),
        parse_mode='HTML'
    )
    
    # Отправляем уведомление новому админу
    try:
        await message.bot.send_message(
            new_admin_id,
            f"🎉 <b>Поздравляем!</b>\n\n"
            f"Вы назначены администратором бота.\n"
            f"Теперь вам доступна админ-панель.\n\n"
            f"Используйте /admin для доступа к функциям администратора.",
            parse_mode='HTML'
        )
    except:
        pass
    
    await state.clear()

@router.callback_query(F.data == "remove_admin")
async def remove_admin_list(callback: CallbackQuery):
    """Показать список админов для удаления"""
    if callback.from_user.id != SUPER_ADMIN_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    # Получаем список админов из БД
    admins = await db.get_all_admins()
    
    if not admins:
        await callback.message.edit_text(
            "📋 <b>Список администраторов пуст</b>\n\n"
            "Нет администраторов для удаления.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_admins")]
            ]),
            parse_mode='HTML'
        )
        return
    
    await callback.message.edit_text(
        "❌ <b>Удаление администратора</b>\n\n"
        "Выберите администратора для удаления:",
        reply_markup=get_admins_list_keyboard(admins, action="del"),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("del_admin_"))
async def remove_admin_confirm(callback: CallbackQuery):
    """Удалить администратора"""
    if callback.from_user.id != SUPER_ADMIN_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    admin_id = int(callback.data.split("_")[2])
    
    # Нельзя удалить супер-админа
    if admin_id == SUPER_ADMIN_ID:
        await callback.answer("❌ Нельзя удалить супер-администратора", show_alert=True)
        return
    
    # Удаляем из базы данных
    await db.remove_admin(admin_id)
    
    # Удаляем из списка ADMIN_IDS
    if admin_id in ADMIN_IDS:
        ADMIN_IDS.remove(admin_id)
    
    await callback.answer("✅ Администратор удален")
    
    # Обновляем список
    await remove_admin_list(callback)
    
    # Отправляем уведомление бывшему админу
    try:
        await callback.bot.send_message(
            admin_id,
            "⚠️ <b>Изменение прав доступа</b>\n\n"
            "Ваши права администратора были отозваны.\n"
            "Админ-панель больше недоступна.",
            parse_mode='HTML'
        )
    except:
        pass

@router.callback_query(F.data == "list_admins")
async def list_admins(callback: CallbackQuery):
    """Показать список всех администраторов"""
    if callback.from_user.id != SUPER_ADMIN_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    # Получаем список админов из БД
    db_admins = await db.get_all_admins()
    
    text = "👥 <b>Список администраторов</b>\n\n"
    
    # Супер-админ
    text += "👑 <b>Супер-администратор:</b>\n"
    try:
        super_admin = await callback.bot.get_chat(SUPER_ADMIN_ID)
        text += f"• {super_admin.first_name} (@{super_admin.username if super_admin.username else 'Нет'}) - ID: {SUPER_ADMIN_ID}\n\n"
    except:
        text += f"• ID: {SUPER_ADMIN_ID}\n\n"
    
    # Обычные админы
    if db_admins:
        text += "👮 <b>Администраторы:</b>\n"
        for admin in db_admins:
            user_id = admin[0]
            username = admin[1] or 'Нет'
            first_name = admin[2] or f'User {user_id}'
            added_at = admin[4]
            
            text += f"• {first_name} (@{username}) - ID: {user_id}\n"
            if added_at:
                text += f"  <i>Добавлен: {added_at.strftime('%d.%m.%Y %H:%M')}</i>\n"
    else:
        text += "<i>Других администраторов нет</i>\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_admins")]
        ]),
        parse_mode='HTML'
    )