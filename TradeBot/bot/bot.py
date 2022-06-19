import io
import logging
import asyncio
import types

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

from keyboards import Keyboards
from states import States
from MathCalc import math_calc
from parser import Parser
from DataBase import DataBase
import GraphMakerPhoto
import GraphMakerHTML
import config

import os

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.token)
dp = Dispatcher(bot, storage=MemoryStorage())

data_base = DataBase(config.mongo_host, config.mongo_port)
keyboards = Keyboards()
parser = Parser()

temp_graph = []  # Данные пользователей, получающих график
temp_upside_buy = []  # Данные пользователей, изменяющих upside и продажу
temp_delete_upside_buy = []  # Данные пользователей, удаляющих upside и продажу
temp_view_buy_sell = []  # Данные пользователей, просматривающих продажу и покупку
temp_picture = []  # Данные пользователей, изменяющих картинку
temp_picture2 = []  # Данные пользователей, просматривающих картинку
temp_insert = []  # Данные пользователей, добавляющих тикер


def get_one_array(array, user_id):
    """Получаем данные по user_id"""
    for value in array:
        if value['user_id'] == user_id:
            return value


def tickers_list(user_id):
    """Список тикеров"""
    tickers = data_base.get_user(user_id)['tickers']
    messages = []
    for ticker in tickers:
        data = f'{ticker["code"]} ({ticker["name"]})\n{ticker["close"] if ticker["close"] else "--"}' \
               f' | {str(ticker["percent"]) + "%" if ticker["percent"] else "--"}' \
               f' | {ticker["upside"] if ticker["upside"] else "--"} | ' \
               f'{ticker["buy"] if ticker["buy"] else "--"}' \
               f'\n/graph_{ticker["code"].lower().replace("^", "__").replace(".", "_")}'
        if ticker['img']:
            data += f'\n/view_{ticker["code"].lower().replace("^", "__").replace(".", "_")}'
        messages.append(data)
    return messages


def ticker_info(ticker):
    """Отправляем информацию о тикере"""
    message_text = f'{ticker["code"]} ({ticker["name"]})\nClose: {ticker["close"] if ticker["close"] else "--"}\n' \
                   f'Sell: {ticker["upside"] if ticker["upside"] else "--"}\n' \
                   f'Buy: {ticker["buy"] if ticker["buy"] else "--"}\n' \
                   f'Percent: {str(ticker["percent"]) + "%" if ticker["percent"] else "--"}\n' \
                   f'/graph_{ticker["code"].lower().replace("^", "__").replace(".", "_")}'
    if ticker['img']:
        message_text += f'\n/view_{ticker["code"].lower().replace("^", "__").replace(".", "_")}'
    return message_text


async def send_view(message):
    """Отправка доп изображения"""
    data = data_base.get_user(message.from_user.id)
    parsed_message = message.text[6:].replace('__', '^').replace('_', '.').upper()

    for ticker in data['tickers']:
        if ticker['code'] == parsed_message and ticker['img']:
            await bot.send_photo(message.from_user.id, ticker['img'], caption=ticker['text'])
            break


@dp.message_handler()
async def start_menu(message: types.Message):
    """Стартовое меню"""
    if message.from_user.id in config.users or message.from_user.id in config.admins:
        data_base.insert_user(message.from_user.id)
        await States.MAIN_MENU.set()
        await message.answer('Доброго времени суток!', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.MAIN_MENU)
async def main_menu(message: types.Message):
    """Главное меню"""
    lowered_message = message.text.lower()

    if lowered_message == 'анализ':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        if tickers:
            await States.ANALYSIS_MENU.set()
            await message.answer('Выберите функцию', reply_markup=keyboards.analysis_menu)
        else:
            await message.answer('У вас нет ни одного тикера')

    elif lowered_message == 'тикер':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        if tickers:
            await States.TICKER_MENU.set()
            await message.answer('Выберите тикер',
                                 reply_markup=keyboards.dynamic(f'{t["code"]} ({t["name"]})' for t in tickers))
        else:
            await message.answer('У вас нет ни одного тикера!')

    elif lowered_message == 'дополнительно':
        await States.PAST_MAIN_MENU.set()
        await message.answer('Выберите функцию', reply_markup=keyboards.past_main_menu)

    elif lowered_message.startswith('/graph_'):
        await send_graph(message)

    elif lowered_message.startswith('/view_'):
        await send_view(message)


@dp.message_handler(state=States.TICKER_MENU)
async def ticker_menu(message: types.Message):
    """Меню тикера"""
    lowered_message = message.text.lower()

    if lowered_message.startswith('/graph_'):
        await send_graph(message)
    elif lowered_message.startswith('/view_'):
        await send_view(message)

    elif lowered_message != 'отмена':
        parsed_message = message.text.split(' ')[0].upper()
        ticker = [t for t in data_base.get_user(message.from_user.id)['tickers'] if t['code'] == parsed_message]

        if ticker:
            await message.answer(ticker_info(ticker[0]), reply_markup=keyboards.goal_keyboard(parsed_message))
        else:
            await message.answer('Неверное имя тикера!')

    else:
        await States.MAIN_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.main_menu)


@dp.callback_query_handler(state='*')
async def process_goal_button(callback_query: types.CallbackQuery):
    """Обработка нажатия на кнопку цели"""
    ticker = [t for t in data_base.get_user(callback_query.from_user.id)['tickers'] if t['code'] == callback_query.data]

    temp_upside_buy.append({'user_id': callback_query.from_user.id, 'code': callback_query.data, 'ticker': ticker[0]})
    await States.BUY_SELL_MENU2.set()
    await bot.send_message(callback_query.from_user.id,
                           f'Значение тек. продажи: {ticker[0]["upside"] if ticker[0]["upside"] else "-"}',
                           reply_markup=keyboards.dynamic(()))


@dp.message_handler(state=States.PAST_MAIN_MENU)
async def past_main_menu(message: types.Message):
    """Меню после главного меню"""
    lowered_message = message.text.lower()

    if lowered_message == 'тикеры':
        await States.TICKERS_MENU.set()
        tickers = tickers_list(message.from_user.id)
        if tickers:
            await message.answer('Выберите функцию', reply_markup=keyboards.tickers_menu)
        else:
            await message.answer('У вас нет ни одного тикера')

    elif lowered_message == 'цели':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        if tickers:
            await States.TARGETS_MENU.set()
            await message.answer('Выберите функцию', reply_markup=keyboards.target_menu)
        else:
            await message.answer('У вас нет ни одного тикера')

    elif lowered_message == 'подписки':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        if tickers:
            await States.PICTURE_MENU.set()
            await message.answer('Выберите функцию', reply_markup=keyboards.picture_menu)
        else:
            await message.answer('У вас нет ни одного тикера')

    elif lowered_message == 'домой':
        await States.MAIN_MENU.set()
        await message.answer('Главное меню', reply_markup=keyboards.main_menu)

    elif lowered_message.startswith('/graph_'):
        await send_graph(message)

    elif lowered_message.startswith('/view_'):
        await send_view(message)


@dp.message_handler(state=States.ANALYSIS_MENU)
async def analysis_menu(message: types.Message):
    """Меню анализа"""
    lowered_message = message.text.lower()
    if lowered_message == 'график':
        await States.GRAPH_MENU1.set()
        await message.answer('Выберите период', reply_markup=keyboards.dynamic(('6 месяцев', '1 год')))

    elif lowered_message == 'таблица':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        await States.TABLE_MENU.set()
        await message.answer('Выберите тикер',
                             reply_markup=keyboards.dynamic(f'{t["code"]} ({t["name"]})' for t in tickers))

    elif lowered_message == 'домой':
        await States.MAIN_MENU.set()
        await message.answer('Главное меню', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.TICKERS_MENU)
async def tickers_menu(message: types.Message):
    """Меню тикеров"""
    lowered_message = message.text.lower()
    if lowered_message == 'список':
        tickers = tickers_list(message.from_user.id)
        if tickers:
            await message.answer('Ваши тикеры', reply_markup=keyboards.tickers_menu)
            for ticker in tickers:
                await message.answer(ticker)
        else:
            await message.answer('У вас нет ни одного тикера')

    elif lowered_message == 'добавить':
        await States.INSERT_MENU1.set()
        await message.answer('Отправьте ссылку', reply_markup=keyboards.dynamic(()))

    elif lowered_message == 'удалить':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        if tickers:
            await States.DELETE_MENU.set()
            await message.answer('Выберите тикер',
                                 reply_markup=keyboards.dynamic(f'{t["code"]} ({t["name"]})' for t in tickers))
        else:
            await message.answer('У вас нет ни одного тикера')

    elif lowered_message.startswith('/graph_'):
        await send_graph(message)

    elif lowered_message.startswith('/view_'):
        await send_view(message)

    elif lowered_message == 'домой':
        await States.MAIN_MENU.set()
        await message.answer('Главное меню', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.TARGETS_MENU)
async def upside_menu(message: types.Message):
    """Меню целей"""
    lowered_message = message.text.lower()
    if lowered_message == 'покупка / продажа':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        await States.BUY_SELL_MENU1.set()
        await message.answer('Выберите тикер',
                             reply_markup=keyboards.dynamic(f'{t["code"]} ({t["name"]})' for t in tickers))

    elif lowered_message == 'удалить':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        await States.DELETE_SELL_BUY_MENU.set()
        await message.answer('Выберите тикер',
                             reply_markup=keyboards.dynamic(f'{t["code"]} ({t["name"]})' for t in tickers))

    elif lowered_message == 'просмотр':
        tickers = data_base.get_user(message.from_user.id)['tickers']
        await States.VIEW_BUY_SELL_MENU.set()
        await message.answer('Выберите тикер',
                             reply_markup=keyboards.dynamic(f'{t["code"]} ({t["name"]})' for t in tickers))

    elif lowered_message.startswith('/graph_'):
        await send_graph(message)

    elif lowered_message.startswith('/view_'):
        await send_view(message)

    elif lowered_message == 'домой':
        await States.MAIN_MENU.set()
        await message.answer('Главное меню', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.PICTURE_MENU)
async def picture_menu(message: types.Message):
    """Меню картинок"""
    lowered_message = message.text.lower()
    if lowered_message == 'просмотр':
        user = data_base.get_user(message.from_user.id)
        parsed_tickers = []
        for i, ticker_data in enumerate(user['user']['tickers']):
            if ticker_data['img']:
                parsed_tickers.append(user['tickers'][i])

        if parsed_tickers:
            temp_picture2.append({'user_id': message.from_user.id, 'tickers': parsed_tickers})
            await States.VIEW_PICTURE_MENU.set()
            await message.answer('Выберите тикер', reply_markup=keyboards.dynamic([f'{t["code"]} {t["name"]}' for t in
                                                                                   parsed_tickers]))
        else:
            await message.answer('У вас нет ни одного тикера с картинкой!')

    elif lowered_message == 'изменить / добавить':
        data = data_base.get_user(message.from_user.id)
        await States.PICTURE_MENU1.set()
        await message.answer('Выберите тикер', reply_markup=keyboards.dynamic([f'{t["code"]} {t["name"]}' for t in
                                                                               data['tickers']]))

    elif lowered_message == 'удалить':
        user = data_base.get_user(message.from_user.id)
        parsed_tickers = []
        for i, ticker_data in enumerate(user['user']['tickers']):
            if ticker_data['img']:
                parsed_tickers.append(user['tickers'][i])

        if parsed_tickers:
            await States.DELETE_PICTURE_MENU.set()
            await message.answer('Выберите тикер',
                                 reply_markup=keyboards.dynamic([f'{t["code"]} {t["name"]}' for t in parsed_tickers]))
        else:
            await message.answer('У вас нет ни одного тикера с картинкой!')

    elif lowered_message == 'домой':
        await States.MAIN_MENU.set()
        await message.answer('Главное меню', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.PICTURE_MENU1)
async def change_picture1(message: types.Message):
    """Меню картинок 1"""
    data = data_base.get_user(message.from_user.id)
    if message.text.lower() != 'отмена':
        parsed_message = message.text.split(' ')[0].upper()
        if parsed_message in [t['code'] for t in data['tickers']]:
            temp_picture.append({'user_id': message.from_user.id,
                                 'code': parsed_message})
            await States.PICTURE_MENU2.set()
            await message.answer('Отправьте изображение (с подписью для добавления подписи)', reply_markup=keyboards.
                                 dynamic(()))
        else:
            await message.answer('Неверное имя тикера!')
    else:
        await States.PICTURE_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.picture_menu)


@dp.message_handler(content_types=['photo', 'text'], state=States.PICTURE_MENU2)
async def change_photo2(message: types.Message):
    """Меню картинок 2"""
    if message.text:
        if message.text.lower() == 'отмена':
            temp_picture.remove(get_one_array(temp_picture, message.from_user.id))
            await States.PICTURE_MENU.set()
            await message.answer('Отмена', reply_markup=keyboards.picture_menu)
        else:
            await message.answer('Отправьте картинку!')
    else:
        data = get_one_array(temp_picture, message.from_user.id)
        bytes_ = await message.photo[-1].download(io.BytesIO())
        if message.caption:
            data_base.add_chart(data['code'], message.from_user.id, bytes_.read(), message.caption)
            temp_picture.remove(data)
            await States.MAIN_MENU.set()
            await message.answer('Операция прошла успешно!', reply_markup=keyboards.main_menu)
        else:
            data['img'] = bytes_.read()
            await States.PICTURE_MENU3.set()
            await message.answer('Введите подпись', reply_markup=keyboards.dynamic(()))


@dp.message_handler(state=States.PICTURE_MENU3)
async def change_picture3(message: types.Message):
    """Меню картинок 3"""
    data = get_one_array(temp_picture, message.from_user.id)
    if message.text.lower() != 'отмена':
        data_base.add_chart(data['code'], message.from_user.id, data['img'], message.text)
    else:
        data_base.add_chart(data['code'], message.from_user.id, data['img'], None)

    temp_picture.remove(data)
    await States.MAIN_MENU.set()
    await message.answer('Операция прошла успешно!', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.DELETE_PICTURE_MENU)
async def delete_picture(message: types.Message):
    """Удаляем картинку"""
    if message.text != 'отмена':
        parsed_message = message.text.split(' ')[0].upper()
        if parsed_message in [t['code'] for t in data_base.get_user(message.from_user.id)['tickers']]:
            data_base.add_chart(parsed_message, message.from_user.id, None, None)
            await States.MAIN_MENU.set()
            await message.answer('Операция прошла успешно!', reply_markup=keyboards.main_menu)
        else:

            await message.answer('Неверное имя тикера!')
    else:
        await States.PICTURE_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.picture_menu)


@dp.message_handler(state=States.VIEW_PICTURE_MENU)
async def view_picture(message: types.Message):
    """Просмотр картинки"""
    data = get_one_array(temp_picture2, message.from_user.id)
    if message.text.lower() != 'отмена':
        ticker = [t for t in data['tickers'] if t['code'] == message.text.split(' ')[0].upper()]
        if ticker:
            temp_picture2.remove(data)
            await States.MAIN_MENU.set()
            await bot.send_photo(message.from_user.id, ticker[0]['img'], caption=ticker[0]['text'],
                                 reply_markup=keyboards.main_menu)
        else:
            await message.answer('Неверное имя тикера!')
    else:
        temp_picture2.remove(data)
        await States.PICTURE_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.picture_menu)


@dp.message_handler(state=States.TABLE_MENU)
async def get_table(message: types.Message):
    """Получаем таблицу"""
    await States.MAIN_MENU.set()
    if message.text.lower() != 'отмена':
        user_tickers = [ticker['code'] for ticker in data_base.get_user(message.from_user.id)['tickers']]
        parsed_message = message.text.split(' ')[0].upper()

        if parsed_message in user_tickers:
            time = datetime.now(pytz.timezone('Europe/Moscow'))
            file_data = math_calc(parser.download_table(datetime(time.year - 1, 1, 1), time, parsed_message),
                                  'table')
            file = types.InputFile(file_data, filename='document.xlsx')
            await bot.send_document(message.chat.id, file, reply_markup=keyboards.main_menu)
        else:
            await message.answer('Неверное имя тикера')

    else:
        await States.ANALYSIS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.analysis_menu)


@dp.message_handler(state=States.GRAPH_MENU1)
async def get_graph1(message: types.Message):
    """Собираем параметры для графика"""
    if message.text.lower() != 'отмена':
        if message.text.lower() == '6 месяцев':
            await States.GRAPH_MENU2.set()
            temp_graph.append({'user_id': message.from_user.id, 'per': 6})
            tickers = data_base.get_user(message.from_user.id)['tickers']
            await message.answer('Выберите тикер: ', reply_markup=keyboards.dynamic(
                f'{t["code"]} ({t["name"]})' for t in tickers))

        elif message.text.lower() == '1 год':
            await States.GRAPH_MENU2.set()
            temp_graph.append({'user_id': message.from_user.id, 'per': 12})
            tickers = data_base.get_user(message.from_user.id)['tickers']
            await message.answer('Выберите тикер: ', reply_markup=keyboards.dynamic(f'{t["code"]} ({t["name"]})' for t
                                                                                    in tickers))
        else:
            await message.answer('Неверный период!')
    else:
        await States.ANALYSIS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.analysis_menu)


@dp.message_handler(state=States.GRAPH_MENU2)
async def get_graph2(message: types.Message):
    """Получаем график"""
    if message.text.lower() != 'отмена':
        await States.MAIN_MENU.set()
        parsed_message = message.text.split(' ')[0].upper()
        ticker = [t for t in data_base.get_user(message.from_user.id)['tickers'] if t['code'] == parsed_message]

        if ticker:
            time = datetime.now(pytz.timezone('Europe/Moscow'))
            table_schedule = math_calc(parser.download_table(time - relativedelta(
                months=get_one_array(temp_graph, message.from_user.id)['per']), time,
                                                             parsed_message), 'graph')
            fig = types.InputFile(GraphMakerPhoto.make_graph(table_schedule, ticker[0]['upside'], ticker[0]['buy']), filename='fig.png')
            await bot.send_photo(message.chat.id, fig, reply_markup=keyboards.main_menu)
            temp_graph.remove(get_one_array(temp_graph, message.from_user.id))
        else:
            await message.answer('Неверное имя тикера')

    else:
        await States.ANALYSIS_MENU.set()
        temp_graph.remove(get_one_array(temp_graph, message.from_user.id))
        await message.answer('Отмена', reply_markup=keyboards.analysis_menu)


@dp.message_handler(state=States.INSERT_MENU1)
async def insert_ticker1(message: types.Message):
    """Собираем данные для добавления нового тикера"""
    if message.text.lower() != 'отмена':
        if message.text.startswith('https://finance.yahoo.com/quote/'):
            result = parser.get_info(message.text)
            if result:
                if result['code'] not in [t['code'] for t in data_base.get_user(message.from_user.id)['tickers']]:
                    await States.INSERT_MENU2.set()
                    temp_insert.append({**result, 'user_id': message.from_user.id, 'upside': 0, 'buy': 0})
                    await message.answer('Введите цель продажи', reply_markup=keyboards.dynamic(()))
                else:
                    await States.MAIN_MENU.set()
                    await message.answer('Вы уже добавили такой тикер!', reply_markup=keyboards.main_menu)
                return

        await States.MAIN_MENU.set()
        await message.answer('Неверная ссылка!', reply_markup=keyboards.main_menu)
    else:
        await States.TICKERS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.tickers_menu)


@dp.message_handler(state=States.INSERT_MENU2)
async def insert_ticker2(message: types.Message):
    """Собираем данные для добавления нового тикера"""
    data = get_one_array(temp_insert, message.from_user.id)
    if message.text.lower() != 'отмена':
        try:
            parsed_message = float(message.text)
            if parsed_message >= 0:

                data['upside'] = parsed_message
                await States.INSERT_MENU3.set()
                await message.answer('Введите цель покупки', reply_markup=keyboards.dynamic(()))

            else:
                await message.answer('Цель продажи не может быть отрицательной!')
        except ValueError:
            await message.answer('Вводите число!')
    else:
        data_base.insert_ticker(data['code'], data['name'], message.from_user.id, data['upside'], data['buy'])
        temp_insert.remove(get_one_array(temp_insert, message.from_user.id))
        await States.MAIN_MENU.set()
        await message.answer('Операция прошла успешно!', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.INSERT_MENU3)
async def insert_ticker3(message: types.Message):
    """Собираем данные для добавления нового тикера"""
    data = get_one_array(temp_insert, message.from_user.id)
    if message.text.lower() != 'отмена':

        try:
            parsed_message = float(message.text)
            if parsed_message >= 0:
                data['buy'] = parsed_message
            else:
                await message.answer('Цель продажи не может быть отрицательной!')
                return
        except ValueError:
            await message.answer('Вводите число!')

    data_base.insert_ticker(data['code'], data['name'], message.from_user.id, data['upside'], data['buy'])
    temp_insert.remove(data)
    await States.MAIN_MENU.set()
    await message.answer('Операция прошла успешно!', reply_markup=keyboards.main_menu)


@dp.message_handler(state=States.DELETE_MENU)
async def delete_ticker(message: types.Message):
    """Удаляем тикер"""
    if message.text.lower() != 'отмена':
        await States.MAIN_MENU.set()
        parsed_message = message.text.split(' ')[0].upper()
        res = data_base.delete_ticker(parsed_message, message.from_user.id)
        await message.answer(res, reply_markup=keyboards.main_menu)
    else:
        await States.TICKERS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.tickers_menu)


@dp.message_handler(state=States.BUY_SELL_MENU1)
async def upside_buy_menu1(message: types.Message):
    """Собираем параметры для продажи и покупки"""
    if message.text.lower() != 'отмена':
        parsed_message = message.text.split(' ')[0].upper()
        ticker = [t for t in data_base.get_user(message.from_user.id)['tickers'] if t['code'] == parsed_message]

        if ticker:
            temp_upside_buy.append({'user_id': message.from_user.id, 'code': parsed_message, 'ticker': ticker[0]})
            await States.BUY_SELL_MENU2.set()
            await message.answer(f'Значение тек. продажи: {ticker[0]["upside"] if ticker[0]["upside"] else "-"}',
                                 reply_markup=keyboards.dynamic(()))
        else:
            await message.answer('Неверное имя тикера!')

    else:
        await States.TARGETS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.target_menu)


@dp.message_handler(state=States.BUY_SELL_MENU2)
async def upside_buy_menu2(message: types.Message):
    """Собираем параметры для продажи и покупки"""
    data = get_one_array(temp_upside_buy, message.from_user.id)
    if message.text.lower() != 'отмена':
        try:
            parsed_message = float(message.text)
            if parsed_message >= 0:
                if parsed_message == int(parsed_message):
                    parsed_message = int(parsed_message)
                data['ticker']['upside'] = parsed_message
                await States.BUY_SELL_MENU3.set()
                await message.answer(f'Значение тек. покупки: '
                                     f'{data["ticker"]["buy"] if data["ticker"]["buy"] else "-"}',
                                     reply_markup=keyboards.dynamic(()))
            else:
                await message.answer('Цена продажи не должна быть отрицательной!')
        except ValueError:
            await message.answer('Вводите число!')

    else:
        temp_upside_buy.remove(data)
        await States.TARGETS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.target_menu)


@dp.message_handler(state=States.BUY_SELL_MENU3)
async def upside_buy_menu3(message: types.Message):
    """Обновляем продажу и покупку"""
    data = get_one_array(temp_upside_buy, message.from_user.id)
    if message.text.lower() != 'отмена':
        try:
            parsed_message = float(message.text)
            if parsed_message >= 0:
                if parsed_message == int(parsed_message):
                    parsed_message = int(parsed_message)
                data["ticker"]["buy"] = parsed_message
                data["ticker"]["percent"] = 0
                data_base.update_upside_buy(data['code'], data["ticker"]["upside"], data["ticker"]["buy"],
                                            message.from_user.id)
                temp_upside_buy.remove(data)
                await States.MAIN_MENU.set()
                await message.answer(ticker_info(data['ticker']), reply_markup=keyboards.main_menu)
            else:
                await message.answer('Цена продажи не должна быть отрицательной!')
        except ValueError:
            await message.answer('Вводите число!')

    else:
        temp_upside_buy.remove(data)
        await States.TARGETS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.target_menu)


@dp.message_handler(state=States.DELETE_SELL_BUY_MENU)
async def delete_upside_buy(message: types.Message):
    """Удалаяем продаже и покупку"""
    if message.text.lower() != 'отмена':
        parsed_message = message.text.split(' ')[0].upper()
        ticker = [t for t in data_base.get_user(message.from_user.id)['tickers'] if t['code'] == parsed_message]

        if ticker:
            ticker[0]["buy"] = 0
            ticker[0]["upside"] = 0
            ticker[0]["percent"] = 0
            data_base.update_upside_buy(parsed_message, 0, 0, message.from_user.id)
            await States.TARGETS_MENU.set()
            await message.answer(ticker_info(ticker[0]), reply_markup=keyboards.target_menu)
        else:
            await message.answer('Неверное имя тикера!', reply_markup=keyboards.target_menu)

    else:
        await States.TARGETS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.target_menu)


@dp.message_handler(state=States.VIEW_BUY_SELL_MENU)
async def view_upside_buy(message: types.Message):
    """Просмотр информации о тикире"""
    if message.text.lower() != 'отмена':
        parsed_message = message.text.split(' ')[0].upper()
        ticker = [t for t in data_base.get_user(message.from_user.id)['tickers'] if t['code'] == parsed_message]

        if ticker:
            await States.TARGETS_MENU.set()
            await message.answer(ticker_info(ticker[0]), reply_markup=keyboards.target_menu)
        else:
            await message.answer('Неверное имя тикера!')

    else:
        await States.TARGETS_MENU.set()
        await message.answer('Отмена', reply_markup=keyboards.target_menu)


async def send_graph(message):
    """Отправляем график"""
    ticker_code = message.text[7:].replace('__', '^').replace('_', '.').upper()
    tickers = data_base.get_user(message.from_user.id)['tickers']
    ticker = [t for t in tickers if t['code'] == ticker_code]
    base_title = f'{ticker[0]["code"]} ({ticker[0]["name"]})'

    time = datetime.now(pytz.timezone('Europe/Moscow'))
    small_table = parser.download_table(time - relativedelta(months=6), time, ticker_code)

    if not small_table.empty:
        small_table.dropna(inplace=True)
        small_table.reset_index(inplace=True, drop=True)
        table_schedule = math_calc(small_table, 'graph')
        if ticker:
            fig = GraphMakerPhoto.make_graph(table_schedule, ticker[0]['upside'], ticker[0]['buy'])
        else:
            fig = GraphMakerPhoto.make_graph(table_schedule, 0, 0)
        await bot.send_photo(message.from_user.id, types.InputFile(fig, filename='fig.png'),
                             caption=f'{base_title} - 6 мес.')

        big_table = parser.download_table(time - relativedelta(years=3), time, ticker_code)
        big_table.dropna(inplace=True)
        big_table.reset_index(inplace=True, drop=True)
        table_schedule = math_calc(big_table, 'graph')
        fig = GraphMakerHTML.candlestick_plot(table_schedule, base_title)
        await bot.send_document(message.from_user.id, types.InputFile(fig, filename=f'{base_title}.html'))
        fig = GraphMakerHTML.candlestick_plot(table_schedule, base_title, 2)
        await bot.send_document(message.from_user.id, types.InputFile(fig, filename=f'{base_title}.html'))


async def auto_sort():
    """Сортируем тикеры"""
    while True:
        time = datetime.now(pytz.timezone('Europe/Moscow'))
        if time.hour == 3:
            for user in data_base.users.find():
                user_data = data_base.get_user(user['user_id'])
                sorted_tickers = sorted(user_data['tickers'], key=lambda x: x['name'])

                parsed_tickers = []
                counter = -1
                while len(user_data['user']['tickers']):
                    counter += 1
                    for ticker in user_data['user']['tickers']:
                        if sorted_tickers[counter]['_id'] == ticker['id']:
                            parsed_tickers.append(ticker)
                            user_data['user']['tickers'].remove(ticker)
                            break

                data_base.users.update_one({'_id': user['_id']},
                                           {'$set': {'tickers': parsed_tickers}})
        await asyncio.sleep(1800)


async def auto_backup():
    """Автоматический бекап БД"""
    time = datetime.now(pytz.timezone('Europe/Moscow'))
    if time.hour == 3:
        if not os.path.exists(config.backup_path):
            os.mkdir(config.backup_path)

        old_backups = os.listdir(config.backup_path)
        os.system(f'docker exec mongo_db_yh sh -c "exec mongodump --db DataBase --gzip --archive" '
                  f'> {os.path.join(config.backup_path, f"backup-{time.year}-{time.month}-{time.day}")}.gz')

        for old_backup in old_backups:
            try:
                os.remove(os.path.join(config.backup_path, old_backup))
            except IsADirectoryError:
                pass
        logging.info(f'{time.year}-{time.month}-{time.day} Backup done')

    await asyncio.sleep(1800)


async def auto_send(send):
    """Расчитываем и отправляем upside, buy, sa1"""
    time = datetime.now(pytz.timezone('Europe/Moscow'))

    data_upside = []
    data_buy = []
    data_sa1 = []

    for ticker in data_base.tickers.find():
        try:
            downloaded_table = parser.download_table(time - relativedelta(days=7), time, ticker['code'])
            if not downloaded_table.empty:

                users = data_base.users.find({'tickers.id': ticker['_id']})
                downloaded_table = parser.download_table(time - relativedelta(months=4), time, ticker['code'])
                row = downloaded_table.loc[downloaded_table.shape[0] - 1]
                rounded_close = round(row['CLOSE'], 2)
                data_base.tickers.update_one({'_id': ticker['_id']}, {'$set': {'close': rounded_close}})

                for user in users:
                    for ticker_ in user['tickers']:
                        if ticker_['id'] == ticker['_id'] and ticker_['upside']:
                            if ticker_['upside'] < row['CLOSE']:
                                percent = round((100 - (ticker_['upside'] * 100 / row['CLOSE'])) + 100)
                                if send:
                                    data_upside.append({'user_id': user['user_id'],
                                                        'name': ticker['name'],
                                                        'code': ticker['code'],
                                                        'close': rounded_close,
                                                        'upside': ticker_['upside'],
                                                        'buy': ticker_['buy'],
                                                        'percent': percent,
                                                        'view': f'/view_{ticker["code"].lower().replace("^", "__").replace(".", "_")}' if
                                                        ticker_['img'] else None
                                                        })
                            else:
                                percent = round((ticker_['upside'] * 100 / row['CLOSE']) - 100)
                            ticker_['percent'] = percent
                            data_base.users.update_one({'user_id': user['user_id']},
                                                       {'$set': {'tickers': user['tickers']}})
                            if send and ticker_['buy'] and ticker_['buy'] > row['CLOSE']:
                                data_buy.append({'user_id': user['user_id'],
                                                 'name': ticker['name'],
                                                 'code': ticker['code'],
                                                 'close': rounded_close,
                                                 'upside': ticker_['upside'],
                                                 'percent': percent,
                                                 'buy': ticker_['buy'],
                                                 'view': f'/view_{ticker["code"].lower().replace("^", "__").replace(".", "_")}' if
                                                 ticker_['img'] else None
                                                 })

                            break

                if send:
                    data = math_calc(downloaded_table, 'auto')
                else:
                    data = None

                users = data_base.users.find({'tickers.id': ticker['_id']})
                parsed_users = []

                for user in users:
                    for ticker_ in user['tickers']:
                        if ticker_['id'] == ticker['_id']:
                            parsed_users.append({
                                'user_id': user['user_id'],
                                'percent': ticker_['percent'],
                                'upside': ticker_['upside'],
                                'buy': ticker_['buy'],
                                'img': ticker_['img']
                            })

                if data:
                    data_sa1.append({**{'name': ticker['name'],
                                        'code': ticker['code'],
                                        'users': [{'user_id': user['user_id'],
                                                   'percent': user['percent'],
                                                   'upside': user['upside'],
                                                   'buy': user['buy'],
                                                   'img': user['img']} for user in
                                                  parsed_users]},
                                     **data})
            await asyncio.sleep(0.01)
        except KeyError:
            pass

    counter = 0
    for upside in data_upside:
        state = dp.current_state(chat=upside['user_id'], user=upside['user_id'])
        await state.set_state(States.MAIN_MENU)
        counter += 1
        if counter == 4:
            await asyncio.sleep(5)
            counter = 0

        data = f'{upside["code"]} ({upside["name"]})\n{upside["close"] if upside["close"] else "--"}' \
               f' | {str(upside["percent"]) + "%" if upside["percent"] else "--"}' \
               f' | {upside["upside"] if upside["upside"] else "--"} | ' \
               f'{upside["buy"] if upside["buy"] else "--"}\nSELL' \
               f'\n/graph_{upside["code"].lower().replace("^", "__").replace(".", "_")}'
        if upside['view']:
            data += f'\n{upside["view"]}'

        await bot.send_message(upside['user_id'], data, reply_markup=keyboards.main_menu)
        await asyncio.sleep(0.01)

    counter = 0
    for buy in data_buy:
        state = dp.current_state(chat=buy['user_id'], user=buy['user_id'])
        await state.set_state(States.MAIN_MENU)
        counter += 1
        if counter == 4:
            await asyncio.sleep(5)
            counter = 0

        data = f'{buy["code"]} ({buy["name"]})\n{buy["close"] if buy["close"] else "--"}' \
               f' | {str(buy["percent"]) + "%" if buy["percent"] else "--"}' \
               f' | {buy["upside"] if buy["upside"] else "--"} | ' \
               f'{buy["buy"] if buy["buy"] else "--"}\nBUY' \
               f'\n/graph_{buy["code"].lower().replace("^", "__").replace(".", "_")}'
        if buy['view']:
            data += f'\n{buy["view"]}'

        await bot.send_message(buy['user_id'], data, reply_markup=keyboards.main_menu)
        await asyncio.sleep(0.01)

    counter = 0
    for sa1 in data_sa1:
        for user in sa1['users']:
            state = dp.current_state(chat=user['user_id'], user=user['user_id'])
            await state.set_state(States.MAIN_MENU)
            counter += 1
            if counter == 4:
                await asyncio.sleep(5)
                counter = 0

            data = f'{sa1["code"]} ({sa1["name"]})\n{sa1["close"] if sa1["close"] else "--"}' \
                   f' | {str(user["percent"]) + "%" if user["percent"] else "--"}' \
                   f' | {user["upside"] if user["upside"] else "--"} | ' \
                   f'{user["buy"] if user["buy"] else "--"}\n{sa1["sa1"]} {sa1["sa1_count"]}' \
                   f'\n/graph_{sa1["code"].lower().replace("^", "__").replace(".", "_")}'
            if user['img']:
                data += f'\n/view_{sa1["code"].lower().replace("^", "__").replace(".", "_")}'

            await bot.send_message(user['user_id'], data, reply_markup=keyboards.main_menu)


async def perform_auto_send():
    """Расчитываем и отправляем upside, buy, sa1"""
    while True:
        time = datetime.now(pytz.timezone('Europe/Moscow'))
        if time.hour == 16 and 19 <= time.minute <= 20 or time.hour == 20 and 39 <= time.minute <= 40:
            if parser.day_info():
                if time.hour == 20:
                    await auto_send(False)
                else:
                    await auto_send(True)

            await asyncio.sleep(3600)
        await asyncio.sleep(60)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(auto_sort())
    loop.create_task(auto_backup())
    loop.create_task(perform_auto_send())

    executor.start_polling(dp, skip_updates=True)
