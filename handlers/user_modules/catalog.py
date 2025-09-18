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

@router.callback_query(F.data == "catalog_brands")
async def callback_catalog_brands(callback: CallbackQuery):
    """Показать каталог по брендам"""
    await page_manager.catalog.show_from_callback(callback, catalog_type='brands')

@router.callback_query(F.data == "catalog_flavors")
async def callback_catalog_flavors(callback: CallbackQuery):
    """Показать каталог по вкусам"""
    await page_manager.catalog.show_from_callback(callback, catalog_type='flavors')

@router.callback_query(F.data.startswith("flavor_"))
async def show_flavor_products(callback: CallbackQuery):
    """Показать товары выбранного вкуса"""
    flavor_id = int(callback.data.split("_")[1])
    await page_manager.catalog.show_from_callback(callback, flavor_id=flavor_id)

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    """Показать карточку товара"""
    data_parts = callback.data.split("_")
    product_id = int(data_parts[1])
    
    # Проверяем, пришли ли из категории или вкуса  
    from_category = None
    if len(data_parts) > 3 and data_parts[2] == "from":
        if data_parts[3] == "flavor":
            # Пришли из вкуса - пока что просто показываем товар
            from_category = None
        else:
            # Пришли из обычной категории
            from_category = int(data_parts[3])
    
    await page_manager.catalog.show_from_callback(callback, product_id=product_id, from_category=from_category)





