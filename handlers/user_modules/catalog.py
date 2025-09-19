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
from utils.loader import show_simple_loader, hide_simple_loader

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
    loader_id = await show_simple_loader(callback, callback.from_user.id, "Загружаем товары...")
    try:
        result = await page_manager.catalog.render(callback.from_user.id, category_id=category_id)
        await hide_simple_loader(loader_id, callback, result['text'], result['keyboard'])
    except Exception as e:
        logger.error(f"Ошибка при загрузке товаров категории: {e}")
        await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "catalog_brands")
async def callback_catalog_brands(callback: CallbackQuery):
    """Показать каталог по брендам"""
    loader_id = await show_simple_loader(callback, callback.from_user.id, "Загружаем бренды...")
    try:
        result = await page_manager.catalog.render(callback.from_user.id, catalog_type='brands')
        await hide_simple_loader(loader_id, callback, result['text'], result['keyboard'])
    except Exception as e:
        logger.error(f"Ошибка при загрузке брендов: {e}")
        await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "catalog_flavors")
async def callback_catalog_flavors(callback: CallbackQuery):
    """Показать каталог по вкусам"""
    loader_id = await show_simple_loader(callback, callback.from_user.id, "Загружаем вкусы...")
    try:
        result = await page_manager.catalog.render(callback.from_user.id, catalog_type='flavors')
        await hide_simple_loader(loader_id, callback, result['text'], result['keyboard'])
    except Exception as e:
        logger.error(f"Ошибка при загрузке вкусов: {e}")
        await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data.startswith("flavor_"))
async def show_flavor_products(callback: CallbackQuery):
    """Показать товары выбранного вкуса"""
    flavor_id = int(callback.data.split("_")[1])
    loader_id = await show_simple_loader(callback, callback.from_user.id, "Загружаем товары...")
    try:
        result = await page_manager.catalog.render(callback.from_user.id, flavor_id=flavor_id)
        await hide_simple_loader(loader_id, callback, result['text'], result['keyboard'])
    except Exception as e:
        logger.error(f"Ошибка при загрузке товаров вкуса: {e}")
        await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка. Попробуйте снова.")

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
    
    loader_id = await show_simple_loader(callback, callback.from_user.id, "Загружаем товар...")
    try:
        result = await page_manager.catalog.render(callback.from_user.id, product_id=product_id, from_category=from_category)
        
        # Если есть фото, нужно обработать отдельно
        if result.get('photo'):
            # Скрываем лоадер, затем отправляем фото с текстом
            await hide_simple_loader(loader_id, callback, "📸 Загружаем фото...")
            try:
                await callback.message.delete()
                await callback.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=result['photo'],
                    caption=result['text'],
                    reply_markup=result['keyboard'],
                    parse_mode='HTML'
                )
            except Exception:
                # Если не удалось с фото, показываем только текст
                await callback.message.answer(
                    result['text'],
                    reply_markup=result['keyboard'],
                    parse_mode='HTML'
                )
        else:
            await hide_simple_loader(loader_id, callback, result['text'], result['keyboard'])
    except Exception as e:
        logger.error(f"Ошибка при загрузке товара: {e}")
        await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка. Попробуйте снова.")





