from aiogram.dispatcher.filters.state import StatesGroup, State


class States(StatesGroup):
    """Машина состояний для бота"""

    MAIN_MENU = State()  # Главное меню
    PAST_MAIN_MENU = State()  # Меню после главного

    TICKER_MENU = State()   # Меня тикера

    GRAPH_MENU1 = State()  # Меню графика 1
    GRAPH_MENU2 = State()  # Меню графика 2
    TABLE_MENU = State()  # Меню таблицы

    INSERT_MENU1 = State()  # Меню добавления тикира 1
    INSERT_MENU2 = State()  # Меню добавления тикира 2
    INSERT_MENU3 = State()  # Меню добавления тикира 3
    DELETE_MENU = State()  # Меню удаления тикира

    BUY_SELL_MENU1 = State()  # Меню покупки/продажи 1
    BUY_SELL_MENU2 = State()  # Меню покупки/продажи 2
    BUY_SELL_MENU3 = State()  # Меню покупки/продажи 3

    DELETE_SELL_BUY_MENU = State()  # Меню удаления покупки/продажи
    VIEW_BUY_SELL_MENU = State()  # Меню просмотра покупи / продажи

    PICTURE_MENU1 = State()  # Меню картинок 1
    PICTURE_MENU2 = State()  # Меню картинок 2
    PICTURE_MENU3 = State()  # Меню картинок 3
    VIEW_PICTURE_MENU = State()  # Просмотр картинок
    DELETE_PICTURE_MENU = State()  # Меню удаление картинки

    ANALYSIS_MENU = State()  # Меню анализа
    TICKERS_MENU = State()  # Меню тикеров
    TARGETS_MENU = State()  # Меню целей
    PICTURE_MENU = State()  # Меню картинок
