"""
Утилиты для работы с временными зонами
"""

from datetime import datetime, timezone, timedelta

# Временная зона Грузии (GMT+4)
GEORGIA_TZ = timezone(timedelta(hours=4))


def to_georgia_time(utc_datetime: datetime) -> datetime:
    """
    Конвертирует UTC время в местное время Грузии (GMT+4)
    
    Args:
        utc_datetime: datetime объект в UTC
        
    Returns:
        datetime объект в местной временной зоне Грузии
    """
    if utc_datetime.tzinfo is None:
        # Если временная зона не указана, предполагаем UTC
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    
    return utc_datetime.astimezone(GEORGIA_TZ)


def format_order_time(utc_datetime: datetime, format_str: str = '%d.%m.%Y %H:%M') -> str:
    """
    Форматирует время заказа с учетом временной зоны Грузии
    
    Args:
        utc_datetime: datetime объект в UTC
        format_str: строка формата времени
        
    Returns:
        Отформатированная строка времени
    """
    georgia_time = to_georgia_time(utc_datetime)
    return georgia_time.strftime(format_str)