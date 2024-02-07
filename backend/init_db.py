import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from fake_useragent import UserAgent
from lxml import etree
from models import *
from backend.database import SqlOperate
import configparser
import json

'''
初始化資料庫
'''


class InitializationDatabase():
    def __init__(self) -> None:
        self.sql_operate = SqlOperate()

        # 讀取授權碼
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.cwa_authorization = config['cwa']['authorization']

        # 初始化連線物件
        self.session = requests.Session()
        retry = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.keep_alive = False

    # 建立並爬取觀測站清單
    def build_station_list(self):

        # 建立資料表
        syntax = """CREATE TABLE IF NOT EXISTS "station_list" (
            "id"	TEXT, -- 測站代碼
            "name"	TEXT, -- 測站名稱
            "alt"	REAL, -- 海拔高度
            "lng"	REAL, -- 經度
            "lat"	REAL, -- 緯度
            "county"	TEXT, -- 縣市
            "addr"	TEXT, -- 地址
            PRIMARY KEY("id")
        );
        """
        self.sql_operate.create_table(syntax)

        # 爬取資料
        url = 'https://e-service.cwa.gov.tw/wdps/obs/state.htm'

        useragent = UserAgent().random
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Dnt': '1',
            'Host': 'e-service.cwa.gov.tw',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': useragent
        }

        response = self.session.get(url, headers=headers, timeout=5)

        if response.status_code == requests.codes.ok:

            station_list = []

            response.encoding = 'utf-8'

            dom = etree.HTML(response.text, etree.HTMLParser())

            station_type_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[3]/text()')  # 型式
            station_id_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[1]/text()')  # 站號
            station_name_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[2]/text()')  # 站名
            station_alt_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[4]/text()')  # 海拔高度
            station_lng_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[5]/text()')  # 經度
            station_lat_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[6]/text()')  # 緯度
            station_county_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[7]/text()')  # 縣市
            station_addr_list = dom.xpath(
                '//*[@id="existing_station"]/table/tr/td[8]/text()')  # 地址

            # 整理資料
            for idx in range(len(station_type_list)):
                if '署屬有人站' == station_type_list[idx] and '雷達' not in station_name_list[idx]:
                    station_list.append({'id': station_id_list[idx],
                                         'name': station_name_list[idx],
                                         'alt': station_alt_list[idx],
                                         'lng': station_lng_list[idx],
                                         'lat': station_lat_list[idx],
                                         'county': station_county_list[idx],
                                         'addr': station_addr_list[idx]
                                         })
            # 寫入資料庫
            self.sql_operate.upsert(StationList, station_list)

    # 建立並爬取即時觀測資料
    def build_realtime_obs(self):
        # 建立資料表
        syntax = """CREATE TABLE IF NOT EXISTS "data_realtime" (
            "id"	TEXT, -- 測站代碼
            "name"	TEXT, -- 測站名稱
            "obs_time"	TEXT, -- 時間
            "Precp"	REAL, -- 降雨量
            "WD"	REAL, -- 風向
            "WS"	REAL, -- 風速
            "Temperature"	REAL, -- 氣溫
            "RH"	INTEGER, -- 相對溼度
            "UVI"	REAL, -- 紫外線
            PRIMARY KEY("id")
        );
            """
        self.sql_operate.create_table(syntax)

        # 查詢所有測站代號
        syntax = """select id, name from station_list"""
        station_list = self.sql_operate.query(syntax)

        stations = ''
        for item in station_list:
            stations = ','.join([stations, item['id']])

        stations = stations[1:]

        # 爬取資料
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={self.cwa_authorization}&StationId={stations}&WeatherElement=Now,WindDirection,WindSpeed,AirTemperature,RelativeHumidity,UVIndex&GeoInfo=Coordinates'
        response = requests.get(url, timeout=5)

        if response.status_code == requests.codes.ok:

            data = response.json()['records']['Station']
            realtime_obs = []

            for item in data:

                weather_element = item['WeatherElement']

                # 整理資料
                rainfall = weather_element['Now']['Precipitation']
                if type(rainfall) != float:
                    rainfall = 0.05
                elif rainfall < 0:
                    rainfall = 0

                realtime_obs.append({
                    'id': item['StationId'],
                    'name': item['StationName'],
                    'obs_time': item['ObsTime']['DateTime'],
                    'Precp': rainfall,
                    'WD': weather_element['WindDirection'],
                    'WS': weather_element['WindSpeed'],
                    'Temperature': weather_element['AirTemperature'],
                    'RH': weather_element['RelativeHumidity'],
                    'UVI': weather_element['UVIndex']
                })

            # 寫入資料庫
            self.sql_operate.upsert(DataRealtime, realtime_obs)

    # 主程式
    def main(self):
        self.build_station_list()
        self.build_realtime_obs()


# if __name__ == "__main__":
#     initialization_database = InitializationDatabase()
#     initialization_database.main()
