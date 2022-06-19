import requests
from bs4 import BeautifulSoup as bs

import time
import pandas as pd
from retry import retry


class Parser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }

    @retry(tries=3, delay=3)
    def get_info(self, url):
        """Получаем данные о котривкое по ссылке"""
        response = requests.get(url, headers=self.headers)

        if response.ok:
            soup = bs(response.text, 'lxml')
            info = soup.find(id='quote-header-info').find(class_='Fz(18px)').text

            ticker = ''
            name = ''
            for symbol in info:
                if not ticker:
                    if symbol != '(':
                        name += symbol
                    else:
                        ticker += ' '
                else:
                    if symbol != ')':
                        ticker += symbol

            return {
                'code': ticker.strip(),
                'name': name.strip()
            }

    @retry(tries=3, delay=3)
    def day_info(self):
        """Проверяем рабочий ли день"""
        response = requests.get('https://finance.yahoo.com/calendar/', headers=self.headers)
        soup = bs(response.text, 'lxml')

        days = soup.find(id='mrt-node-Lead-5-CalEvents')
        current_day = days.find(class_='Bgc($lightBlue)')

        return current_day.find(style='background-color:#ffcfb8') if not current_day.find(style='background-color:#ffcfb8;') else current_day.find(style='background-color:#ffcfb8;')

    @retry(tries=3, delay=80)
    def download_table(self, start_date, end_date, code):
        """Скачиваем таблицу"""
        start_date = round(time.mktime(start_date.timetuple()))
        end_date = round(time.mktime(end_date.timetuple()))

        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{code}?symbol=MSFT&period1={start_date}&period2=' \
              f'{end_date}&interval=1d&includePrePost=true&events=history'

        response = requests.get(url, headers=self.headers)
        if response.ok:
            response_data = response.json()

            data = pd.DataFrame()
            for index, timestamp in enumerate(response_data['chart']['result'][0]['timestamp']):
                data.loc[index, 'DATE'] = pd.to_datetime(timestamp, unit='s')
                data.loc[index, 'HIGH'] = response_data['chart']['result'][0]['indicators']['quote'][0]['high'][index]
                data.loc[index, 'VOLUME'] = response_data['chart']['result'][0]['indicators']['quote'][0]['volume'][index]
                data.loc[index, 'OPEN'] = response_data['chart']['result'][0]['indicators']['quote'][0]['open'][index]
                data.loc[index, 'LOW'] = response_data['chart']['result'][0]['indicators']['quote'][0]['low'][index]
                data.loc[index, 'CLOSE'] = response_data['chart']['result'][0]['indicators']['quote'][0]['close'][index]

            if data.shape[0] >= 4:
                data.dropna(inplace=True)
                data.reset_index(inplace=True, drop=True)
                return data
        return pd.DataFrame()
