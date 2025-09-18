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
            # НЕ создаем новое сообщение - просто логируем ошибку
            await callback.answer("⚠️ Ошибка обновления корзины", show_alert=False)
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
async def callback_cart(callback: CallbackQuery):
    """Показать корзину через callback"""
    await page_manager.cart.show_from_callback(callback)

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Добавить товар в корзину"""
    data_parts = callback.data.split("_")
    product_id = int(data_parts[3])
    
    # Проверяем, есть ли информация о том, из какой категории пришли
    from_category = None
    if len(data_parts) > 5 and data_parts[4] == "from":
        from_category = int(data_parts[5])
    
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
    
    # Проверяем доступное количество с учетом резервов
    available_quantity = await db.get_available_product_quantity(product_id)
    if available_quantity <= 0:
        await callback.answer(
            "❌ Товар закончился или зарезервирован другими покупателями", 
            show_alert=True
        )
        return
    
    # Проверяем, не превышает ли добавление лимит доступного количества
    if current_quantity_in_cart >= available_quantity:
        await callback.answer(
            f"❌ Доступно только {available_quantity} шт. (остальное зарезервировано)", 
            show_alert=True
        )
        return
    
    # Добавляем в корзину с резервированием
    success = await db.add_to_cart(user_id, product_id, current_quantity_in_cart + 1)
    if not success:
        await callback.answer(
            "❌ Товар закончился во время добавления в корзину", 
            show_alert=True
        )
        return
    
    # Получаем количество в корзине после добавления
    cart_items = await db.get_cart(user_id)
    quantity_in_cart = 0
    for item in cart_items:
        if item.product_id == product_id:
            quantity_in_cart = item.quantity
            break
    
    await callback.answer("✅ Товар добавлен в корзину (зарезервирован на 15 мин)", show_alert=False)
    
    # Обновляем текст товара с информацией о количестве в корзине
    product_text = await format_product_card(product, quantity_in_cart, callback.from_user.id)
    
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

@router.callback_query(F.data.startswith("cart_increase_"))
async def cart_increase(callback: CallbackQuery):
    """Увеличить количество товара в корзине"""
    logger.info(f"🔥 HANDLER: cart_increase - callback_data: {callback.data}")
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    async def increase_operation():
        logger.info(f"cart_increase: product_id={product_id}, user_id={user_id}")
        
        # Проверяем товар и его количество на складе
        product = await db.get_product(product_id)
        if not product or not product.in_stock or product.stock_quantity <= 0:
            await callback.answer(_("error.product_unavailable", user_id=callback.from_user.id), show_alert=True)
            return
        
        # Получаем текущее количество
        cart_items = await db.get_cart(user_id)
        current_quantity = 0
        for item in cart_items:
            if item.product_id == product_id:
                current_quantity = item.quantity
                break
        
        # Если товара нет в корзине, значит резерв истек
        if current_quantity == 0:
            await callback.answer("⏰ Время резервирования товара истекло. Товар удален из корзины.", show_alert=True)
            return
        
        # Проверяем доступное количество с учетом резервов
        available_quantity = await db.get_available_product_quantity(product_id)
        
        # Учитываем текущее количество в корзине пользователя (не считаем его как зарезервированное)
        user_cart_quantity = current_quantity
        available_for_user = available_quantity + user_cart_quantity
        
        if current_quantity >= available_for_user:
            await callback.answer(
                f"❌ Доступно только {available_for_user} шт. (остальное зарезервировано)", 
                show_alert=True
            )
            return
        
        new_quantity = current_quantity + 1
        success = await db.update_cart_quantity(user_id, product_id, new_quantity)
        if not success:
            await callback.answer(
                "❌ Товар закончился во время обновления корзины", 
                show_alert=True
            )
            return
        
        await callback.answer(_("cart.quantity_increased", quantity=new_quantity))
        
        # Обновляем отображение корзины через универсальную функцию
        logger.info(f"🛒 CART_INCREASE: Пытаемся обновить корзину для user_id={user_id}")
        cart_updated = await update_cart_display(callback)
        logger.info(f"🛒 CART_INCREASE: cart_updated={cart_updated}")
        
        if not cart_updated:
            # Мы на странице товара - обновляем отображение товара с новым количеством
            logger.info("Обновляем отображение товара...")
            product = await db.get_product(product_id)
            if product:
                # Получаем информацию о количестве в корзине
                cart_items = await db.get_cart(user_id)
                quantity_in_cart = 0
                for item in cart_items:
                    if item.product_id == product_id:
                        quantity_in_cart = item.quantity
                        break
                
                # Формируем обновленный текст товара с количеством
                product_text = await format_product_card(product, quantity_in_cart, user_id)
                
                # Получаем from_category из кнопок
                from_category = None
                for row in callback.message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.callback_data and button.callback_data.startswith("category_"):
                            from_category = int(button.callback_data.split("_")[1])
                            break
                
                # Обновляем сообщение
                keyboard = get_product_card_keyboard(product_id, in_cart=True, from_category=from_category)
                
                # ТОЛЬКО редактируем текущее сообщение, НЕ создаем новое
                try:
                    await callback.message.edit_text(product_text, reply_markup=keyboard, parse_mode='HTML')
                    logger.info("✅ Карточка товара обновлена в cart_increase")
                except Exception as e:
                    logger.warning(f"❌ Не удалось отредактировать карточку товара в cart_increase: {e}")
                    await callback.answer("⚠️ Ошибка обновления", show_alert=False)
    
    await safe_cart_operation(user_id, callback, increase_operation)

@router.callback_query(F.data.startswith("cart_decrease_"))
async def cart_decrease(callback: CallbackQuery):
    """Уменьшить количество товара в корзине"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    async def decrease_operation():
        logger.info(f"cart_decrease: product_id={product_id}, user_id={user_id}")
        
        # Получаем текущее количество
        cart_items = await db.get_cart(user_id)
        current_quantity = 0
        for item in cart_items:
            if item.product_id == product_id:
                current_quantity = item.quantity
                break
        
        # Если товара нет в корзине, значит резерв истек
        if current_quantity == 0:
            await callback.answer("⏰ Время резервирования товара истекло. Товар удален из корзины.", show_alert=True)
            return
        
        if current_quantity <= 1:
            await db.remove_from_cart(user_id, product_id)
            await callback.answer(_("cart.item_deleted"))
        else:
            new_quantity = current_quantity - 1
            await db.update_cart_quantity(user_id, product_id, new_quantity)
            await callback.answer(_("cart.quantity_decreased", quantity=new_quantity))
        
        # Обновляем отображение корзины через универсальную функцию
        logger.info(f"🛒 CART_DECREASE: Пытаемся обновить корзину для user_id={user_id}")
        cart_updated = await update_cart_display(callback)
        logger.info(f"🛒 CART_DECREASE: cart_updated={cart_updated}")
        
        if not cart_updated:
            # Мы на странице товара - обновляем отображение товара
            logger.info("Обновляем отображение товара...")
            product = await db.get_product(product_id)
            if product:
                # Получаем обновленную информацию о количестве в корзине
                cart_items = await db.get_cart(user_id)
                quantity_in_cart = 0
                for item in cart_items:
                    if item.product_id == product_id:
                        quantity_in_cart = item.quantity
                        break
                
                # Формируем обновленный текст товара
                product_text = await format_product_card(product, quantity_in_cart, user_id)
                
                # Получаем from_category из кнопок
                from_category = None
                for row in callback.message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.callback_data and button.callback_data.startswith("category_"):
                            from_category = int(button.callback_data.split("_")[1])
                            break
                
                # Определяем правильную клавиатуру в зависимости от количества
                keyboard = get_product_card_keyboard(product_id, in_cart=(quantity_in_cart > 0), from_category=from_category)
                
                # ТОЛЬКО редактируем текущее сообщение, НЕ создаем новое
                try:
                    await callback.message.edit_text(product_text, reply_markup=keyboard, parse_mode='HTML')
                    logger.info("✅ Карточка товара обновлена в cart_decrease")
                except Exception as e:
                    logger.warning(f"❌ Не удалось отредактировать карточку товара в cart_decrease: {e}")
                    await callback.answer("⚠️ Ошибка обновления", show_alert=False)
    
    await safe_cart_operation(user_id, callback, decrease_operation)

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
    
    # Получаем информацию о товаре
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Получаем текущее количество в корзине
    cart_items = await db.get_cart(user_id)
    current_quantity = 0
    for item in cart_items:
        if item.product_id == product_id:
            current_quantity = item.quantity
            break
    
    # Если товара нет в корзине, значит резерв истек
    if current_quantity == 0:
        await callback.answer("⏰ Время резервирования товара истекло. Товар удален из корзины.", show_alert=True)
        return
    
    # Вычисляем максимальное доступное количество с учетом собственного резерва
    available_quantity = await db.get_available_product_quantity(product_id)
    max_available_for_user = available_quantity + current_quantity
    
    # Сохраняем product_id в состояние
    await state.update_data(cart_product_id=product_id, cart_current_quantity=current_quantity)
    await state.set_state(CartStates.waiting_cart_quantity_input)
    
    # Удаляем старое сообщение корзины и создаем новое с запросом количества
    await message_manager.handle_callback_navigation(
        callback,
        f"🔢 <b>Введите новое количество для товара:</b>\n\n"
        f"🛍️ {product.name}\n"
        f"📦 Текущее количество: {current_quantity} шт.\n"
        f"📦 Всего на складе: {product.stock_quantity} шт.\n"
        f"📦 Доступно для вас: {max_available_for_user} шт.\n\n"
        f"💡 Введите число от 0 до {max_available_for_user}\n"
        f"(0 - удалить товар из корзины)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
        ]),
        menu_state='quantity_input'
    )
    
    await callback.answer()

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
    
    # Проверяем количество
    if quantity < 0:
        error_msg = await message.answer("❌ Количество не может быть отрицательным")
        # Сохраняем ID ошибки для последующего удаления
        await state.update_data(last_error_msg_id=error_msg.message_id)
        return
    
    # Проверяем доступное количество с учетом резервов
    available_quantity = await db.get_available_product_quantity(product_id)
    user_cart_quantity = current_quantity  # Текущее количество в корзине пользователя
    available_for_user = available_quantity + user_cart_quantity
    
    if quantity > available_for_user:
        error_msg = await message.answer(f"❌ Доступно только {available_for_user} шт. (остальное зарезервировано). Попробуйте еще раз:")
        # Сохраняем ID ошибки для последующего удаления
        await state.update_data(last_error_msg_id=error_msg.message_id)
        return
    
    # Получаем ID сообщения с запросом количества для показа лоадера
    loader_message_id = None
    try:
        user_message_data = message_manager.get_user_message(user_id)
        if user_message_data:
            loader_message_id = user_message_data.get('last_message_id')
        logger.info(f"📨 Loader debug: user_message_data={user_message_data}, loader_message_id={loader_message_id}")
    except Exception as e:
        logger.warning(f"❌ Ошибка получения message_id для лоадера: {e}")
        pass
    
    # Показываем лоадер если есть сообщение для редактирования
    loader_id = None
    if loader_message_id:
        logger.info(f"🔄 Пытаемся показать лоадер для message_id={loader_message_id}")
        try:
            loader_id = await loader_manager.show_loader(
                message.bot, 
                user_id, 
                loader_message_id,
                user_id,
                "Обновляем корзину..."
            )
            logger.info(f"✅ Лоадер показан с ID: {loader_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось показать лоадер: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning(f"⚠️ loader_message_id отсутствует, лоадер не будет показан")
    
    try:
        if quantity == 0:
            # Удаляем товар из корзины
            await db.remove_from_cart(user_id, product_id)
        else:
            # Обновляем количество с проверкой наличия
            success = await db.update_cart_quantity(user_id, product_id, quantity)
            if not success:
                # Скрываем лоадер при ошибке
                if loader_id and loader_message_id:
                    await loader_manager.hide_loader(
                        loader_id,
                        message.bot,
                        user_id,
                        loader_message_id,
                        "❌ Товар закончился во время обновления. Попробуйте еще раз:",
                        InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
                        ])
                    )
                else:
                    error_msg = await message.answer("❌ Товар закончился во время обновления. Попробуйте еще раз:")
                    await state.update_data(last_error_msg_id=error_msg.message_id)
                return
        
        # Очищаем состояние (включая ID ошибки)
        await state.clear()
        
        # Получаем обновленную корзину
        page_data = await page_manager.cart.render(user_id)
        
        # Скрываем лоадер и показываем результат
        if loader_id and loader_message_id:
            await loader_manager.hide_loader(
                loader_id,
                message.bot,
                user_id,
                loader_message_id,
                page_data['text'],
                page_data['keyboard']
            )
        else:
            # Если лоадер не работал, используем стандартный способ
            try:
                await message_manager.delete_user_message(message.bot, user_id)
            except:
                pass
            await page_manager.cart.show_from_message(message)
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении корзины: {e}")
        # Скрываем лоадер при любой ошибке
        if loader_id and loader_message_id:
            await loader_manager.hide_loader(
                loader_id,
                message.bot,
                user_id,
                loader_message_id,
                "❌ Произошла ошибка. Попробуйте снова.",
                InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
                ])
            )
        else:
            error_msg = await message.answer("❌ Произошла ошибка. Попробуйте снова.")
            await state.update_data(last_error_msg_id=error_msg.message_id)

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
    
    await callback.answer("❌ Ввод количества отменен")
    
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