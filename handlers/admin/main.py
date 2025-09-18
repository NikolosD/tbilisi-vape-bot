from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import datetime

from database import db
from config import ADMIN_IDS, SUPER_ADMIN_ID
from keyboards import get_enhanced_admin_keyboard
from filters.admin import admin_filter
from i18n import _

# Импортируем роутеры из подмодулей
from .products import router as products_router
from .orders import router as orders_router
from .stats import router as stats_router
from .security import router as security_router
from .categories import router as categories_router
from .communication import router as communication_router
from .flavors import router as flavors_router

# Основной роутер админки
router = Router()

# Подключаем роутеры подмодулей (communication_router первым для приоритета)
router.include_router(communication_router)
router.include_router(products_router)
router.include_router(orders_router)
router.include_router(stats_router)
router.include_router(security_router)
router.include_router(categories_router)
router.include_router(flavors_router)

# Основные состояния админки
class AdminStates(StatesGroup):
    waiting_admin_id = State()

async def is_admin(user_id: int) -> bool:
    """Проверка прав администратора с учетом БД"""
    return user_id in ADMIN_IDS or user_id == SUPER_ADMIN_ID or await db.is_admin_in_db(user_id)

@router.callback_query(F.data == "admin_panel", admin_filter)
async def show_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Показать улучшенную админ панель"""
    await state.clear()
    
    new_orders = await db.get_new_orders()
    checking_orders = await db.get_checking_orders()
    paid_orders = await db.get_paid_orders()
    shipping_orders = await db.get_shipping_orders()
    products = await db.get_all_products()
    
    current_time = datetime.datetime.now().strftime("%H:%M")
    user_id = callback.from_user.id
    
    try:
        await callback.message.edit_text(
            f"{_('admin.enhanced_panel', user_id=user_id)} <i>({current_time})</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_('admin.order_statistics', user_id=user_id)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{_('admin.new_orders', user_id=user_id)} <code>{len(new_orders):>8}</code>\n"
            f"{_('admin.checking_orders', user_id=user_id)} <code>{len(checking_orders):>10}</code>\n" 
            f"{_('admin.confirmed_orders', user_id=user_id)} <code>{len(paid_orders):>6}</code>\n"
            f"{_('admin.shipping_orders', user_id=user_id)} <code>{len(shipping_orders):>9}</code>\n"
            f"{_('admin.total_products', user_id=user_id)} <code>{len(products):>7}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_('admin.select_action', user_id=user_id)}",
            reply_markup=get_enhanced_admin_keyboard(user_id=user_id),
            parse_mode='HTML'
        )
    except Exception:
        await callback.message.delete()
        await callback.message.answer(
            f"{_('admin.enhanced_panel', user_id=user_id)} <i>({current_time})</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_('admin.order_statistics', user_id=user_id)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{_('admin.new_orders', user_id=user_id)} <code>{len(new_orders):>8}</code>\n"
            f"{_('admin.checking_orders', user_id=user_id)} <code>{len(checking_orders):>10}</code>\n" 
            f"{_('admin.confirmed_orders', user_id=user_id)} <code>{len(paid_orders):>6}</code>\n"
            f"{_('admin.shipping_orders', user_id=user_id)} <code>{len(shipping_orders):>9}</code>\n"
            f"{_('admin.total_products', user_id=user_id)} <code>{len(products):>7}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_('admin.select_action', user_id=user_id)}",
            reply_markup=get_enhanced_admin_keyboard(user_id=user_id),
            parse_mode='HTML'
        )

# Обработчик ТОЛЬКО для отклонения платежа (с конкретным состоянием)
from .orders import OrderStates

@router.message(OrderStates.waiting_rejection_reason, F.text, lambda message: message.from_user.id in ADMIN_IDS)
async def process_rejection_reason_main(message: Message, state: FSMContext):
    """Обработка причины отклонения платежа"""
    
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from i18n import _
    
    data = await state.get_data()
    reason = message.text
    
    order_id = data.get('order_id')
    order_number = data.get('order_number')
    user_id = data.get('user_id')
    total_price = data.get('total_price')
    user_lang = data.get('user_lang', 'ru')
    
    if order_id and user_id:
        from database import db
        await db.update_order_status(order_id, 'waiting_payment')
        
        message_text = _("admin.payment_rejected", user_id=user_id, 
                        order_number=order_number, 
                        total_price=total_price,
                        reason=reason)
        
        resend_text = _("admin.resend_screenshot", user_id=user_id)
        contact_text = _("admin.contact_support", user_id=user_id)
        menu_text = _("common.main_menu", user_id=user_id)
        
        try:
            await message.bot.send_message(
                user_id,
                message_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=resend_text, callback_data=f"resend_screenshot_{order_number}")],
                    [InlineKeyboardButton(text=contact_text, callback_data="contact")],
                    [InlineKeyboardButton(text=menu_text, callback_data="back_to_menu")]
                ]),
                parse_mode='HTML'
            )
            await message.answer("✅ Сообщение об отклонении отправлено пользователю!")
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки сообщения: {str(e)}")
    else:
        await message.answer("❌ Ошибка: данные заказа не найдены")
    
    await state.clear()