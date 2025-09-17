"""
Компонент пагинации для многократного использования
"""

from typing import List, Dict, Any, Optional, Callable
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from i18n import _


class PaginationComponent:
    """Универсальный компонент пагинации"""
    
    def __init__(self, items_per_page: int = 5):
        """
        Инициализация компонента пагинации
        
        Args:
            items_per_page: Количество элементов на странице
        """
        self.items_per_page = items_per_page
    
    def paginate(self, items: List[Any], page: int = 1) -> Dict[str, Any]:
        """
        Разбивает список на страницы
        
        Args:
            items: Список элементов для пагинации
            page: Номер текущей страницы (начиная с 1)
            
        Returns:
            Dict с информацией о пагинации:
            {
                'items': [...],  # Элементы текущей страницы
                'page': 1,       # Текущая страница
                'total_pages': 3, # Общее количество страниц
                'total_items': 15, # Общее количество элементов
                'has_prev': False, # Есть ли предыдущая страница
                'has_next': True,  # Есть ли следующая страница
                'start_index': 0,  # Индекс первого элемента на странице
                'end_index': 5     # Индекс последнего элемента на странице
            }
        """
        if not items:
            return {
                'items': [],
                'page': 1,
                'total_pages': 0,
                'total_items': 0,
                'has_prev': False,
                'has_next': False,
                'start_index': 0,
                'end_index': 0
            }
        
        total_items = len(items)
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        
        # Проверяем корректность номера страницы
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
        
        start_index = (page - 1) * self.items_per_page
        end_index = min(start_index + self.items_per_page, total_items)
        page_items = items[start_index:end_index]
        
        return {
            'items': page_items,
            'page': page,
            'total_pages': total_pages,
            'total_items': total_items,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'start_index': start_index,
            'end_index': end_index
        }
    
    def create_pagination_keyboard(
        self,
        pagination_info: Dict[str, Any],
        callback_prefix: str,
        user_id: int,
        item_button_generator: Optional[Callable] = None,
        additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None
    ) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с пагинацией
        
        Args:
            pagination_info: Информация о пагинации из метода paginate()
            callback_prefix: Префикс для callback_data пагинации (например, "orders_page")
            user_id: ID пользователя для переводов
            item_button_generator: Функция для генерации кнопок элементов
                                 Должна принимать (item, index) и возвращать InlineKeyboardButton
            additional_buttons: Дополнительные кнопки для добавления в конец клавиатуры
            
        Returns:
            InlineKeyboardMarkup с элементами и кнопками пагинации
        """
        keyboard = []
        
        # Кнопки для элементов (если есть генератор)
        if item_button_generator and pagination_info['items']:
            for i, item in enumerate(pagination_info['items']):
                button = item_button_generator(item, pagination_info['start_index'] + i)
                if isinstance(button, list):
                    keyboard.append(button)
                else:
                    keyboard.append([button])
        
        # Кнопки пагинации (только если больше одной страницы)
        if pagination_info['total_pages'] > 1:
            pagination_row = []
            
            # Кнопка "Предыдущая"
            if pagination_info['has_prev']:
                pagination_row.append(
                    InlineKeyboardButton(
                        text=f"⬅️ {_('common.prev_page', user_id=user_id)}",
                        callback_data=f"{callback_prefix}_{pagination_info['page'] - 1}"
                    )
                )
            
            # Кнопка "Следующая"
            if pagination_info['has_next']:
                pagination_row.append(
                    InlineKeyboardButton(
                        text=f"{_('common.next_page', user_id=user_id)} ➡️",
                        callback_data=f"{callback_prefix}_{pagination_info['page'] + 1}"
                    )
                )
            
            if pagination_row:
                keyboard.append(pagination_row)
        
        # Дополнительные кнопки
        if additional_buttons:
            keyboard.extend(additional_buttons)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def get_page_info_text(self, pagination_info: Dict[str, Any], user_id: int) -> str:
        """
        Генерирует текст с информацией о странице
        
        Args:
            pagination_info: Информация о пагинации
            user_id: ID пользователя для переводов
            
        Returns:
            Строка вида "📄 Страница 1/3" или пустая строка если одна страница
        """
        if pagination_info['total_pages'] <= 1:
            return ""
        
        return f"📄 {_('common.page', user_id=user_id)} {pagination_info['page']}/{pagination_info['total_pages']}\n\n"


# Глобальный экземпляр для использования во всем приложении
pagination = PaginationComponent()