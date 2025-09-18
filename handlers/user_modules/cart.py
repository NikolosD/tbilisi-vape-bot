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
        
        # Проверяем, не превышает ли увеличение лимит склада
        if current_quantity >= product.stock_quantity:
            await callback.answer(
                _("error.max_quantity", user_id=callback.from_user.id, quantity=product.stock_quantity, current=current_quantity), 
                show_alert=True
            )
            return
        
        new_quantity = current_quantity + 1
        await db.update_cart_quantity(user_id, product_id, new_quantity)
        
        await callback.answer(_("cart.quantity_increased", quantity=new_quantity))
        
        # Проверяем, находимся ли мы на странице товара или в корзине
        message_text = callback.message.text or ""
        if "🛒 Ваша корзина:" in message_text:
            # Мы в корзине - получаем обновленные данные корзины
            logger.info("Обновляем отображение корзины...")
            cart_items = await db.get_cart(user_id)
            
            if not cart_items:
                await message_manager.handle_callback_navigation(
                    callback,
                    "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=_("common.to_catalog"), callback_data="catalog")],
                        [InlineKeyboardButton(text=_("common.main_menu"), callback_data="back_to_menu")]
                    ]),
                    menu_state='cart'
                )
            else:
                total = sum(item.quantity * item.price for item in cart_items)
                cart_text = f"{_('cart.title', user_id=user_id)}\n\n"
                for item in cart_items:
                    cart_text += _("cart.item", 
                                  name=item.name,
                                  quantity=item.quantity, 
                                  price=item.price,
                                  total=item.price * item.quantity,
                                  user_id=user_id)
                cart_text += _("cart.total", total=total, user_id=user_id)
                
                await message_manager.handle_callback_navigation(
                    callback,
                    cart_text,
                    reply_markup=get_cart_keyboard(cart_items),
                    menu_state='cart'
                )
        else:
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
                product_text = format_product_card(product, quantity_in_cart, user_id)
                
                # Получаем from_category из кнопок
                from_category = None
                for row in callback.message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.callback_data and button.callback_data.startswith("category_"):
                            from_category = int(button.callback_data.split("_")[1])
                            break
                
                # Обновляем сообщение
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
        
        if current_quantity <= 1:
            await db.remove_from_cart(user_id, product_id)
            await callback.answer(_("cart.item_deleted"))
        else:
            new_quantity = current_quantity - 1
            await db.update_cart_quantity(user_id, product_id, new_quantity)
            await callback.answer(_("cart.quantity_decreased", quantity=new_quantity))
        
        # Проверяем, находимся ли мы на странице товара или в корзине
        message_text = callback.message.text or ""
        if "🛒 Ваша корзина:" in message_text:
            # Мы в корзине - получаем обновленные данные корзины
            logger.info("Обновляем отображение корзины...")
            cart_items = await db.get_cart(user_id)
            
            if not cart_items:
                await message_manager.handle_callback_navigation(
                    callback,
                    "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=_("common.to_catalog"), callback_data="catalog")],
                        [InlineKeyboardButton(text=_("common.main_menu"), callback_data="back_to_menu")]
                    ]),
                    menu_state='cart'
                )
            else:
                total = sum(item.quantity * item.price for item in cart_items)
                cart_text = f"{_('cart.title', user_id=user_id)}\n\n"
                for item in cart_items:
                    cart_text += _("cart.item", 
                                  name=item.name,
                                  quantity=item.quantity, 
                                  price=item.price,
                                  total=item.price * item.quantity,
                                  user_id=user_id)
                cart_text += _("cart.total", total=total, user_id=user_id)
                
                await message_manager.handle_callback_navigation(
                    callback,
                    cart_text,
                    reply_markup=get_cart_keyboard(cart_items),
                    menu_state='cart'
                )
        else:
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
                product_text = format_product_card(product, quantity_in_cart, user_id)
                
                # Получаем from_category из кнопок
                from_category = None
                for row in callback.message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.callback_data and button.callback_data.startswith("category_"):
                            from_category = int(button.callback_data.split("_")[1])
                            break
                
                # Определяем правильную клавиатуру в зависимости от количества
                keyboard = get_product_card_keyboard(product_id, in_cart=(quantity_in_cart > 0), from_category=from_category)
                
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
        
        # Обновляем корзину если мы на странице корзины
        if "🛒 Ваша корзина:" in callback.message.text:
            logger.info("Обновляем отображение корзины...")
            cart_items = await db.get_cart(user_id)
            
            if not cart_items:
                await message_manager.handle_callback_navigation(
                    callback,
                    "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=_("common.to_catalog"), callback_data="catalog")],
                        [InlineKeyboardButton(text=_("common.main_menu"), callback_data="back_to_menu")]
                    ]),
                    menu_state='cart'
                )
            else:
                total = sum(item.quantity * item.price for item in cart_items)
                cart_text = f"{_('cart.title', user_id=user_id)}\n\n"
                for item in cart_items:
                    cart_text += _("cart.item", 
                                  name=item.name,
                                  quantity=item.quantity, 
                                  price=item.price,
                                  total=item.price * item.quantity,
                                  user_id=user_id)
                cart_text += _("cart.total", total=total, user_id=user_id)
                
                await message_manager.handle_callback_navigation(
                    callback,
                    cart_text,
                    reply_markup=get_cart_keyboard(cart_items),
                    menu_state='cart'
                )
        else:
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
    
    # Сохраняем product_id в состояние
    await state.update_data(cart_product_id=product_id, cart_current_quantity=current_quantity)
    await state.set_state(CartStates.waiting_cart_quantity_input)
    
    # Удаляем старое сообщение корзины и создаем новое с запросом количества
    await message_manager.handle_callback_navigation(
        callback,
        f"🔢 <b>Введите новое количество для товара:</b>\n\n"
        f"🛍️ {product.name}\n"
        f"📦 Текущее количество: {current_quantity} шт.\n"
        f"📦 Доступно на складе: {product.stock_quantity} шт.\n\n"
        f"💡 Введите число от 0 до {product.stock_quantity}\n"
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
    
    if quantity > product.stock_quantity:
        error_msg = await message.answer(f"❌ На складе только {product.stock_quantity} шт. Попробуйте еще раз:")
        # Сохраняем ID ошибки для последующего удаления
        await state.update_data(last_error_msg_id=error_msg.message_id)
        return
    
    if quantity == 0:
        # Удаляем товар из корзины
        await db.remove_from_cart(user_id, product_id)
    else:
        # Обновляем количество
        await db.update_cart_quantity(user_id, product_id, quantity)
    
    # Очищаем состояние (включая ID ошибки)
    await state.clear()
    
    # Удаляем сообщение с запросом количества
    try:
        await message_manager.delete_user_message(message.bot, user_id)
    except:
        pass
    
    # Показываем обновленную корзину с уведомлением об успехе
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
        message.bot, user_id,
        cart_text,
        reply_markup=keyboard,
        menu_state='cart',
        force_new=True  # Создаем новое сообщение чтобы избежать дубликатов
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

async def update_cart_display(callback: CallbackQuery):
    """Обновить отображение корзины"""
    user_id = callback.from_user.id
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        await message_manager.send_or_edit_message(
            callback.bot, user_id,
            "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.to_catalog"), callback_data="catalog")],
                [InlineKeyboardButton(text=_("common.main_menu"), callback_data="back_to_menu")]
            ]),
            menu_state='cart',
            force_new=True
        )
        return
    
    total = sum(item.quantity * item.price for item in cart_items)
    
    cart_text = f"{_('cart.title', user_id=user_id)}\n\n"
    for item in cart_items:
        cart_text += _("cart.item", 
                      name=item.name,
                      quantity=item.quantity, 
                      price=item.price,
                      total=item.price * item.quantity,
                      user_id=user_id)
    
    cart_text += _("cart.total", total=total, user_id=user_id)
    
    await message_manager.send_or_edit_message(
        callback.bot, user_id,
        cart_text,
        reply_markup=get_cart_keyboard(cart_items),
        menu_state='cart',
        force_new=True  # Всегда создаем новое сообщение для корзины чтобы избежать дубликатов
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