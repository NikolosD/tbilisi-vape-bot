from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import db
from filters.admin import admin_filter
from keyboards import get_admin_products_keyboard, get_category_selection_keyboard
from i18n import _

router = Router()

class ProductStates(StatesGroup):
    waiting_product_name = State()
    waiting_product_price = State()
    waiting_product_description = State()
    waiting_product_quantity = State()
    waiting_product_photo = State()
    waiting_quantity_input = State()

@router.callback_query(F.data == "admin_products", admin_filter)
async def admin_products_menu(callback: CallbackQuery):
    """Меню управления товарами"""
    products = await db.get_all_products()
    
    await callback.message.edit_text(
        f"📦 <b>Управление товарами</b>\n\n"
        f"Всего товаров: {len(products)}",
        reply_markup=get_admin_products_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_edit_products", admin_filter)
async def admin_edit_products(callback: CallbackQuery):
    """Показать список товаров для редактирования"""
    products = await db.get_all_products()
    
    if not products:
        await callback.message.edit_text(
            "📦 <b>Товары отсутствуют</b>\n\n"
            "Сначала добавьте товары через меню.",
            reply_markup=get_admin_products_keyboard(),
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {product.name} - {product.price}₾",
                callback_data=f"edit_product_{product.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")])
    
    await callback.message.edit_text(
        "📝 <b>Редактировать товары</b>\n\n"
        "Выберите товар для редактирования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("edit_product_"), admin_filter)
async def edit_product_menu(callback: CallbackQuery):
    """Меню редактирования товара"""
    product_id = int(callback.data.split("_")[2])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer(_("common.not_found", user_id=callback.from_user.id), show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="📦 Изменить количество", callback_data=f"edit_quantity_{product_id}")],
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"delete_product_{product_id}")],
        [InlineKeyboardButton(text="📦 Скрыть/Показать", callback_data=f"toggle_stock_{product_id}")],
        [InlineKeyboardButton(text="🔙 Список товаров", callback_data="admin_edit_products")]
    ]
    
    stock_status = "✅ В наличии" if product.in_stock else "❌ Скрыт"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование товара</b>\n\n"
        f"📝 <b>Название:</b> {product.name}\n"
        f"💰 <b>Цена:</b> {product.price}₾\n"
        f"📋 <b>Описание:</b> {product.description or 'Нет описания'}\n"
        f"📦 <b>Количество:</b> {product.stock_quantity} шт.\n"
        f"📊 <b>Статус:</b> {stock_status}\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("edit_quantity_"), admin_filter)
async def edit_product_quantity(callback: CallbackQuery, state: FSMContext):
    """Изменить количество товара"""
    product_id = int(callback.data.split("_")[2])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer(_("common.not_found", user_id=callback.from_user.id), show_alert=True)
        return
    
    await state.set_state(ProductStates.waiting_quantity_input)
    await state.update_data(product_id=product_id)
    
    await callback.message.edit_text(
        f"📦 <b>Изменение количества</b>\n\n"
        f"📝 <b>Товар:</b> {product.name}\n"
        f"📊 <b>Текущее количество:</b> {product.stock_quantity} шт.\n\n"
        f"Введите новое количество (0-999):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_product_{product_id}")]
        ]),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("delete_product_"), admin_filter)
async def confirm_delete_product(callback: CallbackQuery):
    """Подтверждение удаления товара"""
    product_id = int(callback.data.split("_")[2])
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{product_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_product_{product_id}")]
    ]
    
    await callback.message.edit_text(
        "🗑 <b>Удаление товара</b>\n\n"
        "⚠️ Вы уверены, что хотите удалить этот товар?\n"
        "Это действие нельзя отменить!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("confirm_delete_"), admin_filter)
async def delete_product(callback: CallbackQuery):
    """Удаление товара"""
    product_id = int(callback.data.split("_")[2])
    
    await db.execute("DELETE FROM products WHERE id = $1", product_id)
    
    await callback.message.edit_text(
        "✅ <b>Товар удален!</b>\n\n"
        "Товар успешно удален из каталога.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")]
        ]),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("toggle_stock_"), admin_filter)
async def toggle_product_stock(callback: CallbackQuery):
    """Переключение наличия товара"""
    product_id = int(callback.data.split("_")[2])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer(_("common.not_found", user_id=callback.from_user.id), show_alert=True)
        return
    
    new_stock = not product.in_stock
    await db.update_product_stock(product_id, new_stock)
    
    status_text = "показан в каталоге" if new_stock else "скрыт из каталога"
    
    await callback.answer(f"✅ Товар {status_text}!", show_alert=True)
    
    keyboard = [
        [InlineKeyboardButton(text="📦 Изменить количество", callback_data=f"edit_quantity_{product_id}")],
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"delete_product_{product_id}")],
        [InlineKeyboardButton(text="📦 Скрыть/Показать", callback_data=f"toggle_stock_{product_id}")],
        [InlineKeyboardButton(text="🔙 Список товаров", callback_data="admin_edit_products")]
    ]
    
    stock_status = "✅ В наличии" if new_stock else "❌ Скрыт"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование товара</b>\n\n"
        f"📝 <b>Название:</b> {product.name}\n"
        f"💰 <b>Цена:</b> {product.price}₾\n"
        f"📋 <b>Описание:</b> {product.description or 'Нет описания'}\n"
        f"📦 <b>Количество:</b> {product.stock_quantity} шт.\n"
        f"📊 <b>Статус:</b> {stock_status}\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_add_product", admin_filter)
async def start_add_product(callback: CallbackQuery, state: FSMContext):
    """Начать добавление товара - выбор категории"""
    categories = await db.get_categories()
    
    if not categories:
        await callback.answer("❌ Сначала добавьте категории!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➕ <b>Добавление товара</b>\n\n"
        "Выберите категорию для товара:",
        reply_markup=get_category_selection_keyboard(categories),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("select_category_"), admin_filter)
async def select_category_for_product(callback: CallbackQuery, state: FSMContext):
    """Выбор категории для товара"""
    category_id = int(callback.data.split("_")[2])
    category = await db.get_category(category_id)
    
    await state.update_data(category_id=category_id)
    
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")]
    ]
    
    await callback.message.edit_text(
        f"➕ <b>Добавление товара</b>\n\n"
        f"📂 <b>Категория:</b> {category[2]} {category[1]}\n\n"
        f"Напишите название товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(ProductStates.waiting_product_name)

@router.message(ProductStates.waiting_product_name, admin_filter)
async def process_product_name(message: Message, state: FSMContext):
    """Обработка названия товара"""
    product_name = message.text
    await state.update_data(name=product_name)
    
    await message.answer(
        f"📝 <b>Название:</b> {product_name}\n\n"
        f"Теперь укажите цену товара (в лари):",
        parse_mode='HTML'
    )
    await state.set_state(ProductStates.waiting_product_price)

@router.message(ProductStates.waiting_product_price, admin_filter)
async def process_product_price(message: Message, state: FSMContext):
    """Обработка цены товара"""
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите число больше 0:")
        return
    
    data = await state.get_data()
    await state.update_data(price=price)
    
    await message.answer(
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {price}₾\n\n"
        f"Напишите описание товара:",
        parse_mode='HTML'
    )
    await state.set_state(ProductStates.waiting_product_description)

@router.message(ProductStates.waiting_product_description, admin_filter)
async def process_product_description(message: Message, state: FSMContext):
    """Обработка описания товара"""
    description = message.text
    data = await state.get_data()
    await state.update_data(description=description)
    
    await message.answer(
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {data['price']}₾\n"
        f"📋 <b>Описание:</b> {description}\n\n"
        f"📦 <b>Введите количество товара (1-999):</b>",
        parse_mode='HTML'
    )
    await state.set_state(ProductStates.waiting_product_quantity)

@router.message(ProductStates.waiting_product_quantity, admin_filter)
async def process_product_quantity(message: Message, state: FSMContext):
    """Обработка количества товара"""
    try:
        quantity = int(message.text.strip())
        if quantity < 1 or quantity > 999:
            await message.answer(
                "❌ Количество должно быть от 1 до 999\n\n📦 Введите количество товара:",
                parse_mode='HTML'
            )
            return
    except ValueError:
        await message.answer(
            "❌ Введите число от 1 до 999\n\n📦 Введите количество товара:",
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    await state.update_data(stock_quantity=quantity)
    
    await message.answer(
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {data['price']}₾\n"
        f"📋 <b>Описание:</b> {data['description']}\n"
        f"📦 <b>Количество:</b> {quantity} шт.\n\n"
        f"Теперь пришлите фото товара (или напишите 'пропустить' без фото):",
        parse_mode='HTML'
    )
    await state.set_state(ProductStates.waiting_product_photo)

@router.message(ProductStates.waiting_product_photo, F.content_type == 'photo', admin_filter)
async def process_product_photo(message: Message, state: FSMContext):
    """Обработка фото товара"""
    photo_file_id = message.photo[-1].file_id
    data = await state.get_data()
    
    await db.add_product(
        name=data['name'],
        price=data['price'],
        description=data['description'],
        photo=photo_file_id,
        category_id=data.get('category_id'),
        stock_quantity=data.get('stock_quantity', 1)
    )
    
    await message.answer(
        f"✅ <b>Товар добавлен!</b>\n\n"
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {data['price']}₾\n"
        f"📋 <b>Описание:</b> {data['description']}\n"
        f"📦 <b>Количество:</b> {data.get('stock_quantity', 1)} шт.\n"
        f"📸 <b>Фото:</b> Добавлено",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить еще товар", callback_data="admin_add_product")],
            [InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_products")],
            [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_panel")]
        ]),
        parse_mode='HTML'
    )
    
    await state.clear()

@router.message(ProductStates.waiting_product_photo, F.text == "пропустить", admin_filter)
async def process_product_no_photo(message: Message, state: FSMContext):
    """Добавление товара без фото"""
    data = await state.get_data()
    
    await db.add_product(
        name=data['name'],
        price=data['price'],
        description=data['description'],
        photo=None,
        category_id=data.get('category_id'),
        stock_quantity=data.get('stock_quantity', 1)
    )
    
    await message.answer(
        f"✅ <b>Товар добавлен!</b>\n\n"
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {data['price']}₾\n"
        f"📋 <b>Описание:</b> {data['description']}\n"
        f"📦 <b>Количество:</b> {data.get('stock_quantity', 1)} шт.\n"
        f"📸 <b>Фото:</b> Не добавлено",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить еще товар", callback_data="admin_add_product")],
            [InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_products")],
            [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_panel")]
        ]),
        parse_mode='HTML'
    )
    
    await state.clear()

@router.message(ProductStates.waiting_quantity_input, admin_filter)
async def process_quantity_input(message: Message, state: FSMContext):
    """Обработка ввода нового количества товара"""
    try:
        quantity = int(message.text.strip())
        if quantity < 0 or quantity > 999:
            await message.answer(
                "❌ Количество должно быть от 0 до 999\n\n📦 Введите новое количество:",
                parse_mode='HTML'
            )
            return
    except ValueError:
        await message.answer(
            "❌ Введите число от 0 до 999\n\n📦 Введите новое количество:",
            parse_mode='HTML'
        )
        return
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    await db.execute("UPDATE products SET stock_quantity = $1 WHERE id = $2", quantity, product_id)
    
    product = await db.get_product(product_id)
    
    await message.answer(
        f"✅ <b>Количество обновлено!</b>\n\n"
        f"📝 <b>Товар:</b> {product.name}\n"
        f"📦 <b>Новое количество:</b> {quantity} шт.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_product_{product_id}")],
            [InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_products")]
        ]),
        parse_mode='HTML'
    )
    
    await state.clear()