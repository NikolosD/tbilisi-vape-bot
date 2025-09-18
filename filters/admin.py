from config import ADMIN_IDS, SUPER_ADMIN_ID

def admin_filter(message_or_callback):
    """Проверка прав администратора"""
    user_id = message_or_callback.from_user.id
    is_admin = user_id in ADMIN_IDS or user_id == SUPER_ADMIN_ID
    print(f"🔒 DEBUG: Admin filter check for user {user_id}: {is_admin} (ADMIN_IDS: {ADMIN_IDS})")
    return is_admin