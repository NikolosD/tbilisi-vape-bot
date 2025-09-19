from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from database import db
from keyboards import (
    get_cart_keyboard, get_product_card_keyboard, get_back_to_menu_keyboard
)
from message_manager import message_manager
from i18n import _
from button_filters import is_cart_button
from pages.manager import page_manager
from utils.formatters import format_product_card, format_cart_display
from utils.loader import loader_manager

# Импортируем функцию для удаления сообщений с задержкой
async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds):
    """Удалить сообщение через указанное количество секунд"""
    import asyncio
    logger.info(f"Ожидание {delay_seconds} секунд перед удалением сообщения {message_id}")
    await asyncio.sleep(delay_seconds)
    try:
        logger.info(f"Удаляем сообщение {message_id}")
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Сообщение {message_id} успешно удалено")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")

async def update_cart_display(callback: CallbackQuery):
    """Универсальная функция для обновления отображения корзины"""
    user_id = callback.from_user.id
    
    # Проверяем, находимся ли мы в корзине (точная проверка)
    message_text = callback.message.text or ""
    logger.info(f"🔍 Проверяем текст сообщения: '{message_text[:50]}...'")
    
    # Корзина должна НАЧИНАТЬСЯ с "🛒 Ваша корзина:" или содержать "💰 Итого:"
    is_cart_page = (
        message_text.startswith("🛒 Ваша корзина:") or 
        "🛒 Ваша корзина:" in message_text or
        "💰 Итого:" in message_text
    )
    
    logger.info(f"🔍 is_cart_page: {is_cart_page}")
    
    if is_cart_page:
        # Проверяем, была ли корзина с товарами до обновления
        had_cart_items = "💰 Итого:" in message_text
        
        # Мы в корзине - обновляем её через стандартную компоненту
        logger.info("Обновляем отображение корзины через page_manager...")
        
        # Получаем обновленные данные корзины через стандартную страницу
        page_data = await page_manager.cart.render(user_id)
        
        # Проверяем, стала ли корзина пустой после обновления
        cart_became_empty = had_cart_items and "пуста" in page_data['text']
        
        if cart_became_empty:
            # Если корзина стала пустой, значит резерв истек
            logger.info("🕐 Резерв корзины истек, уведомляем пользователя")
            await callback.answer("⏰ Время резервирования товаров истекло. Корзина очищена.", show_alert=True)
        
        # ТОЛЬКО редактируем текущее сообщение, никогда не создаем новое
        try:
            await callback.message.edit_text(
                page_data['text'],
                reply_markup=page_data['keyboard'],
                parse_mode='HTML'
            )
            logger.info("✅ Корзина успешно обновлена без создания нового сообщения")
        except Exception as e:
            logger.warning(f"❌ Не удалось отредактировать сообщение корзины: {e}")
            # Показываем временное сообщение об ошибке
            error_msg = await callback.message.answer(
                "⚠️ <b>Ошибка обновления корзины</b>\n\n"
                "Попробуйте перейти в корзину заново",
                parse_mode='HTML'
            )
            # Удаляем сообщение об ошибке через 3 секунды
            import asyncio
            asyncio.create_task(delete_message_after_delay(callback.bot, callback.message.chat.id, error_msg.message_id, 3))
        return True
    return False

logger = logging.getLogger(__name__)

router = Router()

# Словарь для предотвращения одновременных операций с корзиной одного пользователя
user_cart_operations = {}

async def safe_cart_operation(user_id: int, callback: CallbackQuery, operation_func):
    """Безопасная операция с корзиной - предотвращает race conditions"""
    # Проверяем, есть ли уже активная операция для этого пользователя
    if user_id in user_cart_operations:
        # Используем всплывающее уведомление для быстрого уведомления о блокировке
        await callback.answer("⏳ Подождите, операция выполняется...", show_alert=False)
        return
    
    try:
        # Отмечаем что операция начата
        user_cart_operations[user_id] = True
        await operation_func()
    finally:
        # Убираем флаг после завершения
        user_cart_operations.pop(user_id, None)

class CartStates(StatesGroup):
    waiting_cart_quantity_input = State()

# Обработчик текстовых сообщений из главного меню
@router.message(is_cart_button)
async def show_cart(message: Message):
    """Показать корзину"""
    print(f"🛒 CART DEBUG: Handler called for text '{message.text}' from user {message.from_user.id}")
    try:
        await page_manager.cart.show_from_message(message)
        print(f"🛒 CART DEBUG: show_from_message completed successfully")
    except Exception as e:
        print(f"🛒 CART ERROR: {e}")
        import traceback
        traceback.print_exc()

@router.callback_query(F.data == "cart")
async def callback_cart(callback: CallbackQuery, state: FSMContext):
    """Показать корзину через callback"""
    # Показываем лоадер
    from utils.loader import show_simple_loader, hide_simple_loader
    loader_id = await show_simple_loader(callback, callback.from_user.id, "Загружаем корзину...")
    
    try:
        # Очищаем состояние если пользователь был в процессе оформления заказа
        await state.clear()
        
        # Получаем данные корзины
        result = await page_manager.cart.render(callback.from_user.id)
        
        # Скрываем лоадер и показываем корзину
        await hide_simple_loader(loader_id, callback, result['text'], result['keyboard'])
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке корзины: {e}")
        await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка при загрузке корзины. Попробуйте снова.")

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Добавить товар в корзину (оптимизированная версия)"""
    data_parts = callback.data.split("_")
    product_id = int(data_parts[3])
    
    # Проверяем, есть ли информация о том, из какой категории пришли
    from_category = None
    if len(data_parts) > 5 and data_parts[4] == "from":
        from_category = int(data_parts[5])
    
    user_id = callback.from_user.id
    
    # Показываем лоадер
    from utils.loader import show_simple_loader, hide_simple_loader
    loader_id = await show_simple_loader(callback, user_id, "Добавляем в корзину...")
    
    try:
    
        # ОПТИМИЗАЦИЯ: Используем fast-проверку товара с доступным количеством
        product = await db.get_product_with_availability(product_id)
        if not product or not product.in_stock or product.stock_quantity <= 0:
            await hide_simple_loader(loader_id, callback, "❌ Товар недоступен")
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
    
        # ОПТИМИЗАЦИЯ: Быстрая проверка количества конкретного товара в корзине
        current_quantity_in_cart = await db.get_product_quantity_in_cart(user_id, product_id)
        
        # Используем уже вычисленное доступное количество
        available_quantity = product.stock_quantity
        if available_quantity <= 0:
            await hide_simple_loader(loader_id, callback, "❌ Товар закончился или зарезервирован другими покупателями")
            return
        
        # Проверяем, не превышает ли добавление лимит доступного количества
        if current_quantity_in_cart >= available_quantity:
            await hide_simple_loader(loader_id, callback, f"❌ Доступно только {available_quantity} шт. (остальное зарезервировано)")
            return
        
        # Добавляем в корзину с резервированием
        success = await db.add_to_cart(user_id, product_id, current_quantity_in_cart + 1)
        if not success:
            await hide_simple_loader(loader_id, callback, "❌ Товар закончился во время добавления в корзину")
            return
    
        # ОПТИМИЗАЦИЯ: Вычисляем новое количество вместо еще одного запроса
        quantity_in_cart = current_quantity_in_cart + 1
        
        # ОПТИМИЗАЦИЯ: Используем быстрый форматтер без дополнительных запросов к БД
        from utils.formatters import format_product_card_fast
        product_text = format_product_card_fast(product, quantity_in_cart, callback.from_user.id)
        
        # ОПТИМИЗАЦИЯ: Сразу обновляем исходное сообщение товара
        keyboard = get_product_card_keyboard(product_id, in_cart=True, from_category=from_category)
        
        # Скрываем лоадер и показываем результат
        await hide_simple_loader(loader_id, callback, product_text, keyboard)
        
        # Уведомление об успехе
        await callback.answer("✅ Товар добавлен в корзину!", show_alert=False)
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении товара в корзину: {e}")
        try:
            await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка. Попробуйте снова.")
        except:
            pass



@router.callback_query(F.data.startswith("cart_remove_"))
async def cart_remove(callback: CallbackQuery):
    """Удалить товар из корзины"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    async def remove_operation():
        logger.info(f"cart_remove: product_id={product_id}, user_id={user_id}")
        
        product = await db.get_product(product_id)
        await db.remove_from_cart(user_id, product_id)
        
        await callback.answer(_("cart.item_removed"))
        
        # Обновляем отображение корзины через универсальную функцию
        cart_updated = await update_cart_display(callback)
        
        if not cart_updated:
            # Получаем from_category из исходного callback_data если есть
            original_data = callback.message.reply_markup.inline_keyboard
            from_category = None
            for row in original_data:
                for button in row:
                    if button.callback_data and button.callback_data.startswith("category_"):
                        from_category = int(button.callback_data.split("_")[1])
                        break
            
            # Обновляем кнопки на странице товара
            keyboard = get_product_card_keyboard(product_id, in_cart=False, from_category=from_category)
            await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    await safe_cart_operation(user_id, callback, remove_operation)

@router.callback_query(F.data.startswith("cart_input_qty_"))
async def cart_input_quantity(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод количества товара в корзине"""
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    # Показываем лоадер
    from utils.loader import show_simple_loader, hide_simple_loader
    loader_id = await show_simple_loader(callback, user_id, "Загружаем информацию о товаре...")
    
    try:
        # ОПТИМИЗАЦИЯ: Получаем информацию о товаре с доступным количеством
        product = await db.get_product_with_availability(product_id)
        if not product:
            await hide_simple_loader(loader_id, callback, "❌ Товар не найден")
            return
        
        # ОПТИМИЗАЦИЯ: Быстрая проверка количества конкретного товара в корзине
        current_quantity = await db.get_product_quantity_in_cart(user_id, product_id)
        
        # Если товара нет в корзине, значит резерв истек
        if current_quantity == 0:
            await hide_simple_loader(loader_id, callback, "⏰ Время резервирования товара истекло. Товар удален из корзины.")
            return
        
        # ОПТИМИЗАЦИЯ: Используем уже вычисленное доступное количество
        available_quantity = product.stock_quantity
        max_available_for_user = available_quantity + current_quantity
        
        # Сохраняем product_id в состояние
        await state.update_data(cart_product_id=product_id, cart_current_quantity=current_quantity)
        await state.set_state(CartStates.waiting_cart_quantity_input)
        
        # Скрываем лоадер и показываем форму ввода количества
        await hide_simple_loader(
            loader_id, 
            callback,
            f"🔢 <b>Введите новое количество для товара:</b>\n\n"
            f"🛍️ {product.name}\n"
            f"📦 Текущее количество: {current_quantity} шт.\n"
            f"📦 Всего на складе: {product.stock_quantity} шт.\n"
            f"📦 Доступно для вас: {max_available_for_user} шт.\n\n"
            f"💡 Введите число от 0 до {max_available_for_user}\n"
            f"(0 - удалить товар из корзины)",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Ошибка при запросе ввода количества: {e}")
        await hide_simple_loader(loader_id, callback, "❌ Произошла ошибка. Попробуйте снова.")

@router.message(CartStates.waiting_cart_quantity_input)
async def process_cart_quantity_input(message: Message, state: FSMContext):
    """Обработать ввод количества для корзины"""
    user_id = message.from_user.id
    
    try:
        quantity = int(message.text)
    except ValueError:
        error_msg = await message.answer("❌ Пожалуйста, введите число")
        # Сохраняем ID ошибки для последующего удаления
        await state.update_data(last_error_msg_id=error_msg.message_id)
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data.get('cart_product_id')
    current_quantity = data.get('cart_current_quantity', 0)
    
    # Удаляем предыдущую ошибку если есть
    last_error_msg_id = data.get('last_error_msg_id')
    if last_error_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=last_error_msg_id)
        except:
            pass
    
    if not product_id:
        await message.answer("❌ Ошибка. Попробуйте снова.")
        await state.clear()
        return
    
    # Получаем товар для проверки наличия
    product = await db.get_product(product_id)
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return
    
    # Удаляем сообщение пользователя сразу
    try:
        await message.delete()
    except:
        pass
    
    # Удаляем старое сообщение с запросом количества
    try:
        await message_manager.delete_user_message(message.bot, user_id)
    except:
        pass
    
    # Создаем анимированный лоадер
    from utils.loader import show_simple_loader, hide_simple_loader
    loader_message = await message.answer("⏳ Обновляем корзину...")
    loader_id = await show_simple_loader(
        type('MockCallback', (), {
            'message': loader_message,
            'from_user': type('User', (), {'id': user_id})(),
            'bot': message.bot
        })(),
        user_id, 
        "Обновляем корзину..."
    )
    
    # Проверяем количество
    if quantity < 0:
        await hide_simple_loader(
            loader_id, 
            type('MockCallback', (), {
                'message': loader_message,
                'from_user': type('User', (), {'id': user_id})(),
                'bot': message.bot
            })(),
            "❌ Количество не может быть отрицательным",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
            ])
        )
        return
    
    # Проверяем доступное количество с учетом резервов
    available_quantity = await db.get_available_product_quantity(product_id)
    user_cart_quantity = current_quantity  # Текущее количество в корзине пользователя
    available_for_user = available_quantity + user_cart_quantity
    
    if quantity > available_for_user:
        await hide_simple_loader(
            loader_id, 
            type('MockCallback', (), {
                'message': loader_message,
                'from_user': type('User', (), {'id': user_id})(),
                'bot': message.bot
            })(),
            f"❌ Доступно только {available_for_user} шт. (остальное зарезервировано). Попробуйте еще раз:",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
            ])
        )
        return
    
    try:
        if quantity == 0:
            # Удаляем товар из корзины
            await db.remove_from_cart(user_id, product_id)
        else:
            # Обновляем количество с проверкой наличия
            success = await db.update_cart_quantity(user_id, product_id, quantity)
            if not success:
                # Показываем ошибку
                await hide_simple_loader(
                    loader_id, 
                    type('MockCallback', (), {
                        'message': loader_message,
                        'from_user': type('User', (), {'id': user_id})(),
                        'bot': message.bot
                    })(),
                    "❌ Товар закончился во время обновления. Попробуйте еще раз:",
                    InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
                    ])
                )
                return
        
        # Очищаем состояние (включая ID ошибки)
        await state.clear()
        
        # Получаем обновленную корзину
        page_data = await page_manager.cart.render(user_id)
        
        # Скрываем лоадер и показываем результат
        await hide_simple_loader(
            loader_id, 
            type('MockCallback', (), {
                'message': loader_message,
                'from_user': type('User', (), {'id': user_id})(),
                'bot': message.bot
            })(),
            page_data['text'],
            page_data['keyboard']
        )
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении корзины: {e}")
        # Показываем ошибку
        await hide_simple_loader(
            loader_id, 
            type('MockCallback', (), {
                'message': loader_message,
                'from_user': type('User', (), {'id': user_id})(),
                'bot': message.bot
            })(),
            "❌ Произошла ошибка. Попробуйте снова.",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
            ])
        )

@router.callback_query(F.data == "cancel_quantity_input")
async def cancel_quantity_input(callback: CallbackQuery, state: FSMContext):
    """Отмена ввода количества"""
    user_id = callback.from_user.id
    await state.clear()
    
    # Удаляем сообщение с запросом количества
    try:
        await message_manager.delete_user_message(callback.bot, user_id)
    except:
        pass
    
    # Показываем временное сообщение об отмене
    cancel_msg = await callback.message.answer(
        "❌ <b>Ввод количества отменен</b>\n\n"
        "Возвращаемся к корзине...",
        parse_mode='HTML'
    )
    
    # Удаляем уведомление через 2 секунды
    import asyncio
    asyncio.create_task(delete_message_after_delay(callback.bot, callback.message.chat.id, cancel_msg.message_id, 2))
    
    # Возвращаемся к корзине, используя message_manager
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        cart_text = "🛒 Ваша корзина пуста"
        keyboard = get_back_to_menu_keyboard()
    else:
        total = sum(item.price * item.quantity for item in cart_items)
        cart_text = f"🛒 Ваша корзина:\n\n"
        
        for item in cart_items:
            cart_text += f"🛍️ {item.name}\n"
            cart_text += f"📦 {item.quantity} шт. × {item.price}₾ = {item.price * item.quantity}₾\n\n"
        
        cart_text += f"💰 Итого: {total}₾"
        
        keyboard = get_cart_keyboard(cart_items)
    
    # Используем message_manager для правильного управления сообщениями
    await message_manager.send_or_edit_message(
        callback.bot, user_id,
        cart_text,
        reply_markup=keyboard,
        menu_state='cart',
        force_new=True  # Создаем новое сообщение чтобы избежать дубликатов
    )


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    """Очистить корзину"""
    user_id = callback.from_user.id
    await db.clear_cart(user_id)
    
    await message_manager.handle_callback_navigation(
        callback,
        "🗑 <b>Корзина очищена</b>\n\nДобавьте товары из каталога!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("common.to_catalog", user_id=user_id), callback_data="catalog")],
            [InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="back_to_menu")]
        ]),
        menu_state='cart_cleared'
    )