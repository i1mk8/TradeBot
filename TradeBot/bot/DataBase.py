from pymongo import MongoClient


class DataBase:
    """Работаем с БД"""

    def __init__(self, host, port):
        self.cluster = MongoClient(host, port)
        self.db = self.cluster['DataBase']
        self.users = self.db['users']
        self.tickers = self.db['tickers']

    def insert_user(self, user_id):
        """Добовляем нового пользователя"""
        if not self.users.count_documents({'user_id': user_id}):
            self.users.insert_one({'user_id': user_id, 'tickers': []})

    def get_user(self, user_id):
        """Получаем пользователя"""
        user = self.users.find_one({'user_id': user_id})
        tickers = [{**self.tickers.find_one({'_id': t['id']}),
                    'upside': t['upside'],
                    'percent': t['percent'],
                    'buy': t['buy'],
                    'img': t['img'],
                    'text': t['text']} for t in user['tickers']]
        return {
            'user': user,
            'tickers': tickers
        }

    def insert_ticker(self, ticker_code, ticker_name, user_id, upside, buy):
        """Добавляем новый тикер"""
        if not self.tickers.count_documents({'code': ticker_code}):
            ticker_id = self.tickers.insert_one({'name': ticker_name, 'code': ticker_code, 'close': 0}).inserted_id
        else:
            ticker_id = self.tickers.find_one({'code': ticker_code})['_id']

        if upside == int(upside):
            upside = int(upside)

        if buy == int(buy):
            buy = int(buy)

        self.users.update_one({'user_id': user_id}, {'$push': {'tickers': {'id': ticker_id,
                                                                       'upside': upside,
                                                                       'percent': 0,
                                                                       'buy': buy,
                                                                       'img': None,
                                                                       'text': None}}})

    def delete_ticker(self, ticker_code, user_id):
        """Удаляем тикер"""
        ticker = [t for t in self.get_user(user_id)['tickers'] if t['code'] == ticker_code]
        if ticker:
            self.users.update_one({'user_id': user_id}, {'$pull': {'tickers': {'id': ticker[0]['_id']}}})

            if not self.users.count_documents({'tickers.id': ticker[0]['_id']}):
                self.tickers.delete_one({'_id': ticker[0]['_id']})

            return 'Операция прошла успешно'
        return 'У вас нет такого тикера'

    def update_upside_buy(self, ticker_code, upside, buy, user_id):
        """Обновляем апсайд"""
        user_data = self.get_user(user_id)

        for i, ticker in enumerate(user_data['tickers']):
            if ticker_code == ticker['code']:

                if upside == round(upside):
                    upside = round(upside)
                if buy == round(buy):
                    buy = round(buy)

                user_data['user']['tickers'][i]['upside'] = upside
                user_data['user']['tickers'][i]['buy'] = buy
                user_data['user']['tickers'][i]['percent'] = 0
                self.users.update_one({'user_id': user_id}, {'$set': {'tickers': user_data['user']['tickers']}})
                return user_data['user']['tickers'][i]

    def add_chart(self, ticker_code, user_id, chart_bytes, text):
        """Добавляем график для пользователя"""
        user = self.get_user(user_id)

        for i, ticker in enumerate(user['tickers']):
            if ticker_code == ticker['code']:
                user['user']['tickers'][i]['img'] = chart_bytes
                user['user']['tickers'][i]['text'] = text
                self.users.update_one({'user_id': user_id}, {'$set': {'tickers': user['user']['tickers']}})
