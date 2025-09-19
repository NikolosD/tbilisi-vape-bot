"""
Админ модуль для управления категориями вкусов
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from filters.admin import admin_filter
from i18n import _
from utils.safe_operations import safe_edit_message

router = Router()

# Состояния для управления вкусами
class FlavorStates(StatesGroup):
    waiting_flavor_name = State()
    waiting_flavor_emoji = State()
    waiting_flavor_description = State()
    editing_flavor_name = State()
    editing_flavor_emoji = State()
    editing_flavor_description = State()

@router.callback_query(F.data == "admin_flavors", admin_filter)
async def show_flavor_management(callback: CallbackQuery, state: FSMContext):
    """Показать управление категориями вкусов"""
    await state.clear()
    
    flavor_categories = await db.get_flavor_categories()
    
    text = "🍓 <b>Управление категориями вкусов</b>\n\n"
    
    if flavor_categories:
        text += f"📋 Всего категорий: {len(flavor_categories)}\n\n"
        for flavor in flavor_categories:
            products_count = len(await db.get_products_by_flavor(flavor.id))
            text += f"{flavor.emoji} <b>{flavor.name}</b> ({products_count} товаров)\n"
    else:
        text += "📦 Категории вкусов не созданы"
    
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_flavor")],
        [InlineKeyboardButton(text="📋 Управлять категориями", callback_data="manage_flavors")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "add_flavor", admin_filter)
async def add_flavor_start(callback: CallbackQuery, state: FSMContext):
    """Начать добавление новой категории вкуса"""
    text = "🍓 <b>Добавление новой категории вкуса</b>\n\n" \
           "Введите название категории (например: Фруктовые):"
    
    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_flavors")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await state.set_state(FlavorStates.waiting_flavor_name)

@router.message(FlavorStates.waiting_flavor_name)
async def add_flavor_name(message: Message, state: FSMContext):
    """Получить название категории вкуса"""
    if len(message.text) > 100:
        await message.answer("❌ Название слишком длинное (максимум 100 символов)")
        return
    
    await state.update_data(name=message.text)
    
    text = f"🍓 <b>Добавление категории: {message.text}</b>\n\n" \
           "Теперь введите эмодзи для категории (например: 🍓, ❄️, 🍊):"
    
    keyboard = [
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_flavor_emoji")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_flavors")]
    ]
    
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await state.set_state(FlavorStates.waiting_flavor_emoji)

@router.message(FlavorStates.waiting_flavor_emoji)
async def add_flavor_emoji(message: Message, state: FSMContext):
    """Получить эмодзи категории вкуса"""
    if len(message.text) > 10:
        await message.answer("❌ Эмодзи слишком длинное (максимум 10 символов)")
        return
    
    await state.update_data(emoji=message.text)
    
    data = await state.get_data()
    text = f"🍓 <b>Добавление категории: {data['name']}</b>\n" \
           f"Эмодзи: {message.text}\n\n" \
           "Введите описание категории (необязательно):"
    
    keyboard = [
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_flavor_description")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_flavors")]
    ]
    
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await state.set_state(FlavorStates.waiting_flavor_description)

@router.callback_query(F.data == "skip_flavor_emoji", admin_filter)
async def skip_flavor_emoji(callback: CallbackQuery, state: FSMContext):
    """Пропустить эмодзи"""
    await state.update_data(emoji='')
    
    data = await state.get_data()
    text = f"🍓 <b>Добавление категории: {data['name']}</b>\n\n" \
           "Введите описание категории (необязательно):"
    
    keyboard = [
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_flavor_description")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_flavors")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await state.set_state(FlavorStates.waiting_flavor_description)

@router.message(FlavorStates.waiting_flavor_description)
async def add_flavor_description(message: Message, state: FSMContext):
    """Получить описание и создать категорию"""
    await state.update_data(description=message.text)
    await finish_adding_flavor(message, state)

@router.callback_query(F.data == "skip_flavor_description", admin_filter)
async def skip_flavor_description(callback: CallbackQuery, state: FSMContext):
    """Пропустить описание и создать категорию"""
    await state.update_data(description='')
    await finish_adding_flavor(callback.message, state, is_callback=True)

async def finish_adding_flavor(message, state: FSMContext, is_callback=False):
    """Завершить создание категории вкуса"""
    data = await state.get_data()
    
    try:
        # Создаем категорию в БД
        category_id = await db.add_flavor_category(
            name=data['name'],
            emoji=data.get('emoji', ''),
            description=data.get('description', '')
        )
        
        text = f"✅ <b>Категория создана!</b>\n\n" \
               f"{data.get('emoji', '🍃')} <b>{data['name']}</b>\n" \
               f"ID: {category_id}\n"
        
        if data.get('description'):
            text += f"Описание: {data['description']}\n"
        
        keyboard = [
            [InlineKeyboardButton(text="🔙 К управлению вкусами", callback_data="admin_flavors")]
        ]
        
        if is_callback:
            await message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
        
        await state.clear()
        
    except Exception as e:
        error_text = f"❌ Ошибка при создании категории: {str(e)}"
        keyboard = [
            [InlineKeyboardButton(text="🔙 К управлению вкусами", callback_data="admin_flavors")]
        ]
        
        if is_callback:
            await message.edit_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        else:
            await message.answer(
                error_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        await state.clear()

@router.callback_query(F.data == "manage_flavors", admin_filter)
async def manage_flavors_list(callback: CallbackQuery, state: FSMContext):
    """Показать список категорий для управления"""
    await state.clear()
    
    flavor_categories = await db.get_flavor_categories()
    
    if not flavor_categories:
        text = "📦 Категории вкусов не созданы\n\n" \
               "Создайте первую категорию!"
        keyboard = [
            [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_flavor")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_flavors")]
        ]
    else:
        text = "📋 <b>Выберите категорию для управления:</b>\n\n"
        
        keyboard = []
        for flavor in flavor_categories:
            products_count = len(await db.get_products_by_flavor(flavor.id))
            button_text = f"{flavor.emoji} {flavor.name} ({products_count} товаров)"
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"edit_flavor_{flavor.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_flavors")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("edit_flavor_"), admin_filter)
async def edit_flavor_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования категории вкуса"""
    flavor_id = int(callback.data.split("_")[2])
    flavor = await db.get_flavor_category(flavor_id)
    
    if not flavor:
        await callback.answer("❌ Категория не найдена")
        return
    
    products_count = len(await db.get_products_by_flavor(flavor_id))
    
    text = f"✏️ <b>Редактирование категории</b>\n\n" \
           f"{flavor.emoji} <b>{flavor.name}</b>\n" \
           f"ID: {flavor.id}\n" \
           f"Товаров: {products_count}\n"
    
    if flavor.description:
        text += f"Описание: {flavor.description}\n"
    
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_flavor_name_{flavor_id}")],
        [InlineKeyboardButton(text="🎨 Изменить эмодзи", callback_data=f"edit_flavor_emoji_{flavor_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_flavor_desc_{flavor_id}")],
        [InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"delete_flavor_{flavor_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_flavors")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("delete_flavor_"), admin_filter)
async def confirm_delete_flavor(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления категории"""
    flavor_id = int(callback.data.split("_")[2])
    flavor = await db.get_flavor_category(flavor_id)
    
    if not flavor:
        await callback.answer("❌ Категория не найдена")
        return
    
    products_count = len(await db.get_products_by_flavor(flavor_id))
    
    text = f"⚠️ <b>Удаление категории</b>\n\n" \
           f"{flavor.emoji} <b>{flavor.name}</b>\n"
    
    if products_count > 0:
        text += f"\n❗ У {products_count} товаров будет удалена привязка к этой категории!\n"
    
    text += "\nВы уверены, что хотите удалить эту категорию?"
    
    keyboard = [
        [InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"confirm_delete_flavor_{flavor_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_flavor_{flavor_id}")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_delete_flavor_"), admin_filter)
async def delete_flavor_confirmed(callback: CallbackQuery, state: FSMContext):
    """Удалить категорию вкуса"""
    flavor_id = int(callback.data.split("_")[3])
    
    try:
        flavor = await db.get_flavor_category(flavor_id)
        if flavor:
            await db.delete_flavor_category(flavor_id)
            
            text = f"✅ <b>Категория удалена</b>\n\n" \
                   f"Категория '{flavor.name}' успешно удалена"
        else:
            text = "❌ Категория не найдена"
        
    except Exception as e:
        text = f"❌ Ошибка при удалении: {str(e)}"
    
    keyboard = [
        [InlineKeyboardButton(text="🔙 К управлению вкусами", callback_data="admin_flavors")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )