from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


class Keyboards:
    """Клавиатуры для бота"""
    def __init__(self):
        self.main_menu = ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура главного меню
        self.main_menu.row(KeyboardButton('Тикер'), KeyboardButton('Дополнительно'))

        self.past_main_menu = ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура после главного меню
        self.past_main_menu.row(KeyboardButton('Тикеры'), KeyboardButton('Цели'), KeyboardButton('Подписки'))
        self.past_main_menu.row((KeyboardButton('Домой')))

        self.analysis_menu = ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура анализа
        self.analysis_menu.row(KeyboardButton('График'), KeyboardButton('Таблица'))
        self.analysis_menu.row(KeyboardButton('Домой'))

        self.tickers_menu = ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура тикеров
        self.tickers_menu.row(KeyboardButton('Добавить'), KeyboardButton('Удалить'))
        self.tickers_menu.row(KeyboardButton('Список'), KeyboardButton('Домой'))

        self.target_menu = ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура целей
        self.target_menu.row(KeyboardButton('Покупка / Продажа'), KeyboardButton('Удалить'))
        self.target_menu.row(KeyboardButton('Просмотр'), KeyboardButton('Домой'))

        self.picture_menu = ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура картинок
        self.picture_menu.row(KeyboardButton('Изменить / Добавить'), KeyboardButton('Удалить'))
        self.picture_menu.row(KeyboardButton('Просмотр'), KeyboardButton('Домой'))

    def dynamic(self, items):
        """Динамическая клавиатура"""
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        [keyboard.add(KeyboardButton(btn)) for btn in list(items) + ['Отмена']]
        return keyboard

    def goal_keyboard(self, ticker_code):
        """Инлайн кнопка целей"""
        inline_button = InlineKeyboardButton('Цели', callback_data=ticker_code)
        inline_keyboard = InlineKeyboardMarkup().add(inline_button)
        return inline_keyboard

    # def graph_keyboard(self, message):
    #     """Генерируем клавиаутру для графика"""
    #     ticker_code = message[7:].replace('__', '^').replace('_', '.').upper()
    #     graph_menu = InlineKeyboardMarkup()
    #     graph_menu.add(InlineKeyboardButton('6 мес.', callback_data=f'6;{ticker_code}'))
    #     graph_menu.add(InlineKeyboardButton('12 мес.', callback_data=f'12;{ticker_code}'))
    #     return graph_menu
