from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from filters.admin import admin_filter
from keyboards import get_admin_categories_keyboard
from utils.safe_operations import safe_edit_message

router = Router()

class CategoryStates(StatesGroup):
    waiting_category_name = State()
    waiting_category_emoji = State()
    waiting_category_description = State()

@router.callback_query(F.data == "admin_categories", admin_filter)
async def show_admin_categories(callback: CallbackQuery):
    """Показать управление категориями"""
    await callback.message.edit_text(
        "🏷️ <b>Управление категориями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_categories_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_add_category", admin_filter)
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    """Начать добавление категории"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление категориями", callback_data="admin_categories")]
    ]
    
    await callback.message.edit_text(
        "➕ <b>Добавление категории</b>\n\n"
        "Напишите название категории:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(CategoryStates.waiting_category_name)

@router.message(CategoryStates.waiting_category_name, admin_filter)
async def process_category_name(message: Message, state: FSMContext):
    """Обработка названия категории"""
    category_name = message.text
    await state.update_data(name=category_name)
    
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление категориями", callback_data="admin_categories")]
    ]
    
    await message.answer(
        f"➕ <b>Добавление категории</b>\n\n"
        f"📝 <b>Название:</b> {category_name}\n\n"
        f"Напишите эмодзи для категории (например: 🧚, 💨, 🔥):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(CategoryStates.waiting_category_emoji)

@router.message(CategoryStates.waiting_category_emoji, admin_filter)
async def process_category_emoji(message: Message, state: FSMContext):
    """Обработка эмодзи категории"""
    emoji = message.text
    data = await state.get_data()
    await state.update_data(emoji=emoji)
    
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление категориями", callback_data="admin_categories")]
    ]
    
    await message.answer(
        f"➕ <b>Добавление категории</b>\n\n"
        f"📝 <b>Название:</b> {emoji} {data['name']}\n\n"
        f"Напишите описание категории (или отправьте 'пропустить'):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(CategoryStates.waiting_category_description)

@router.message(CategoryStates.waiting_category_description, admin_filter)
async def process_category_description(message: Message, state: FSMContext):
    """Обработка описания категории"""
    data = await state.get_data()
    description = message.text if message.text != "пропустить" else None
    
    await db.add_category(
        name=data['name'],
        emoji=data['emoji'],
        description=description
    )
    
    await message.answer(
        f"✅ <b>Категория добавлена!</b>\n\n"
        f"📝 <b>Название:</b> {data['emoji']} {data['name']}\n"
        f"📄 <b>Описание:</b> {description or 'Не указано'}",
        reply_markup=get_admin_categories_keyboard(),
        parse_mode='HTML'
    )
    
    await state.clear()