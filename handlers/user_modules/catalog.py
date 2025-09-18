from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import logging

from database import db
from keyboards import get_product_card_keyboard
from message_manager import message_manager
from i18n import _
from button_filters import is_catalog_button
from pages.manager import page_manager
from utils.formatters import format_product_card

logger = logging.getLogger(__name__)

router = Router()


# Обработчик текстовых сообщений из главного меню
@router.message(is_catalog_button)
async def show_catalog(message: Message):
    """Показать каталог категорий"""
    print(f"🛍 CATALOG DEBUG: Handler called for text '{message.text}' from user {message.from_user.id}")
    try:
        await page_manager.catalog.show_from_message(message)
        print(f"🛍 CATALOG DEBUG: show_from_message completed successfully")
    except Exception as e:
        print(f"🛍 CATALOG ERROR: {e}")
        import traceback
        traceback.print_exc()

# Обработчики callback-запросов
@router.callback_query(F.data == "catalog")
async def callback_catalog(callback: CallbackQuery):
    """Показать каталог категорий через callback"""
    await page_manager.catalog.show_from_callback(callback)

@router.callback_query(F.data.startswith("category_"))
async def show_category_products(callback: CallbackQuery):
    """Показать товары выбранной категории"""
    category_id = int(callback.data.split("_")[1])
    await page_manager.catalog.show_from_callback(callback, category_id=category_id)

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    """Показать карточку товара"""
    data_parts = callback.data.split("_")
    product_id = int(data_parts[1])
    
    # Проверяем, пришли ли из категории  
    from_category = None
    if len(data_parts) > 3 and data_parts[2] == "from":
        from_category = int(data_parts[3])
    
    await page_manager.catalog.show_from_callback(callback, product_id=product_id, from_category=from_category)

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Добавить товар в корзину"""
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    # Проверяем существование товара
    product = await db.get_product(product_id)
    if not product or not product.in_stock or product.stock_quantity <= 0:
        await callback.answer(_("common.error"), show_alert=True)
        return
    
    # Убеждаемся, что пользователь существует в базе
    user = await db.get_user(user_id)
    if not user:
        # Определяем язык пользователя из Telegram
        user_lang = 'ru'  # По умолчанию русский
        if callback.from_user.language_code:
            if callback.from_user.language_code.startswith('ka'):
                user_lang = 'ka'
            elif callback.from_user.language_code.startswith('en'):
                user_lang = 'en'
        
        # Добавляем пользователя в базу
        await db.add_user(
            user_id=user_id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            language_code=user_lang
        )
    
    # Проверяем текущее количество в корзине
    cart_items = await db.get_cart(user_id)
    current_quantity_in_cart = 0
    for item in cart_items:
        if item.product_id == product_id:
            current_quantity_in_cart = item.quantity
            break
    
    # Проверяем, не превышает ли добавление лимит склада
    if current_quantity_in_cart >= product.stock_quantity:
        await callback.answer(
            _("error.max_quantity", user_id=callback.from_user.id, quantity=product.stock_quantity, current=current_quantity_in_cart), 
            show_alert=True
        )
        return
    
    # Добавляем в корзину
    await db.add_to_cart(user_id, product_id, 1)
    
    # Получаем количество в корзине после добавления
    cart_items = await db.get_cart(user_id)
    quantity_in_cart = 0
    for item in cart_items:
        if item.product_id == product_id:
            quantity_in_cart = item.quantity
            break
    
    await callback.answer(_("cart.item_added"))
    
    # Получаем from_category из исходного callback_data если есть
    original_data = callback.message.reply_markup.inline_keyboard
    from_category = None
    for row in original_data:
        for button in row:
            if button.callback_data and button.callback_data.startswith("category_"):
                from_category = int(button.callback_data.split("_")[1])
                break
    
    # Обновляем текст товара с информацией о количестве в корзине
    product_text = format_product_card(product, quantity_in_cart, callback.from_user.id)
    
    # Обновляем сообщение с новым текстом и кнопками
    keyboard = get_product_card_keyboard(product_id, in_cart=True, from_category=from_category)
    
    # Пытаемся отредактировать текущее сообщение
    try:
        await callback.message.edit_text(product_text, reply_markup=keyboard, parse_mode='HTML')
    except Exception:
        # Если не получается отредактировать, удаляем и создаем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        await message_manager.send_or_edit_message(
            callback.bot, user_id,
            product_text,
            reply_markup=keyboard,
            menu_state='product_view',
            force_new=True
        )




