from config import ADMIN_IDS, SUPER_ADMIN_ID

def admin_filter(message_or_callback):
    """Проверка прав администратора"""
    user_id = message_or_callback.from_user.id
    return user_id in ADMIN_IDS or user_id == SUPER_ADMIN_ID