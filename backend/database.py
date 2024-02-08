from tqdm import tqdm
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Session, sessionmaker
from .models import *
import time
import random
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib import parse
from fake_useragent import UserAgent
from lxml import etree
import configparser
import datetime
import arrow
import threading
from concurrent.futures import ThreadPoolExecutor


class SqlOperate:
    '''
    資料庫操作
    '''

    def __init__(self) -> None:
        DATABASE_URL = f"sqlite:///data/weather.db"
        self.sqlite_engine = create_engine(DATABASE_URL)

    # 查詢資料
    def query(self, syntax):
        with Session(self.sqlite_engine) as session:
            result = session.execute(text(syntax))
            data = result.fetchall()
            column_names = result.keys()

            query_result = [dict(zip(column_names, row)) for row in data]

        return query_result

    # 建立表格
    def create_table(self, syntax):
        with Session(self.sqlite_engine) as session:
            session.execute(text(syntax))
            session.commit()
            table_name = syntax.split('"')[1]
            print(f'資料表 {table_name} 建立成功！')

    # 新增或更新資料
    def upsert(self, table, data, batch_size=10000):
        # 取得資料表名稱
        tablename = table.__tablename__

        # 取得主鍵
        primary_key_columns = [
            column.name for column in table.__table__.columns if column.primary_key]

        # 取得更新資料的欄位
        set_dict = {}
        for key, value in data[0].items():
            if key not in primary_key_columns:
                set_dict[key] = getattr(sqlite.insert(table).excluded, key)

        # 將資料分割為多個批次
        batches = []
        for idx in range(0, len(data), batch_size):
            batch = data[idx: idx + batch_size]
            batches.append(batch)

        # 批次新增或更新資料
        with Session(self.sqlite_engine) as session:
            session.begin()

            try:
                for batch_data in tqdm(batches, desc=f'資料表 {tablename} 寫入進度'):
                    insert_stmt = sqlite.insert(table).values(batch_data)
                    on_conflict_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=primary_key_columns, set_=set_dict)

                    session.execute(on_conflict_stmt)
                session.commit()

            except Exception as e:
                session.rollback()
                print(e)


class DataPipeline():
    '''
    資料處理
    '''

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

    """
    使用多線程處理資料

    Args:
    - task: 處理每個資料項目的函式
    - data: 要處理的資料列表
    - max_workers: 同時運行的最大執行緒數量

    Returns:
    - 處理完成的結果列表
    """
    # 多工處理

    def __multitasking(self, task, data,  max_workers=4):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(task, item) for item in data]
            return [future.result() for future in futures]

    # 發送請求(GET方法)
    def __web_requests_get(self, url, headers=None):

        response = self.session.get(url, headers=headers, timeout=5)

        while response.status_code != requests.codes.ok:
            t = random.uniform(0.5, 2.5)
            time.sleep(t)
            response = self.session.get(url, headers=headers, timeout=5)

        self.session.close()

        return response

    # 建立並爬取觀測站清單
    def build_station_list(self):
        syntax = """
            CREATE TABLE IF NOT EXISTS "station_list" (
                "sID"	TEXT, -- 測站代碼
                "name"	TEXT, -- 測站名稱
                "alt"	REAL, -- 海拔高度
                "lon"	REAL, -- 經度
                "lat"	REAL, -- 緯度
                "county"	TEXT, -- 縣市
                "addr"	TEXT, -- 地址
                PRIMARY KEY("sID")
            );
        """
        self.sql_operate.create_table(syntax)

        # 建構請求資料
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

        # 爬取資料
        response = self.__web_requests_get(url, headers)
        response.encoding = 'utf-8'
        dom = etree.HTML(response.text, etree.HTMLParser())

        station_list = []

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
                station_list.append({'sID': station_id_list[idx],
                                    'name': station_name_list[idx],
                                     'alt': station_alt_list[idx],
                                     'lon': station_lng_list[idx],
                                     'lat': station_lat_list[idx],
                                     'county': station_county_list[idx],
                                     'addr': station_addr_list[idx]
                                     })
        # 寫入資料庫
        self.sql_operate.upsert(StationList, station_list)

    # 建立即時觀測資料表
    def build_realtime_obs(self):
        syntax = """
            CREATE TABLE IF NOT EXISTS "data_realtime" (
                "sID"	TEXT, -- 測站代碼
                "name"	TEXT, -- 測站名稱
                "obs_time"	INTEGER, -- 時間
                "Precp"	REAL, -- 降雨量
                "WD"	REAL, -- 風向
                "WS"	REAL, -- 風速
                "Temperature"	REAL, -- 氣溫
                "RH"	INTEGER, -- 相對溼度
                "UVI"	REAL, -- 紫外線
                PRIMARY KEY("sID")
            );
        """
        self.sql_operate.create_table(syntax)

    # 爬取並寫入即時觀測資料
    def crawler_realtime_obs(self):

        # 查詢所有測站代號
        syntax = """SELECT sID, name FROM station_list"""
        station_list = self.sql_operate.query(syntax)

        stations = ''
        for item in station_list:
            stations = ','.join([stations, item['sID']])

        stations = stations[1:]

        # 爬取資料
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={self.cwa_authorization}&StationId={stations}&WeatherElement=Now,WindDirection,WindSpeed,AirTemperature,RelativeHumidity,UVIndex&GeoInfo=Coordinates'
        response = self.__web_requests_get(url)

        data = response.json()['records']['Station']

        # 轉換並整理資料
        def extract_realtime_obs(item):

            weather_element = item['WeatherElement']

            # 整理降雨資料
            rainfall = weather_element['Now']['Precipitation']
            if type(rainfall) != float:
                rainfall = 0.05
            elif rainfall < 0:
                rainfall = 0

            # 轉換時間格式
            obs_time = datetime.datetime.strptime(
                item['ObsTime']['DateTime'], "%Y-%m-%dT%H:%M:%S%z").timestamp()
            obs_time = int(obs_time)

            return {
                'sID': item['StationId'],
                'name': item['StationName'],
                'obs_time': obs_time,
                'Precp': rainfall,
                'WD': weather_element['WindDirection'],
                'WS': weather_element['WindSpeed'],
                'Temperature': weather_element['AirTemperature'],
                'RH': weather_element['RelativeHumidity'],
                'UVI': weather_element['UVIndex']
            }
        # 使用多線程處理資料
        process_result = self.multitasking(extract_realtime_obs, data)

        # 寫入資料庫
        self.sql_operate.upsert(DataRealtime, process_result)

    # 建立歷史觀測資料表
    def build_history_obs(self):
        syntax = """
            CREATE TABLE IF NOT EXISTS "data_history" (
                "sID"	TEXT, -- 測站代碼
                "name"	TEXT, -- 測站名稱
                "obs_date"	INTEGER, -- 資料日期
                "Temperature"	REAL, -- 氣溫
                "Tmax"	REAL, -- 最高氣溫
                "Tmin"	REAL, -- 最低氣溫
                "Precp"	REAL, -- 降雨量
                "PrecpHour"	REAL, -- 降雨時數 
                "RH"	REAL, -- 相對溼度
                "StnPres"	REAL, -- 測站氣壓
                "SeaPres"	REAL, -- 海平面氣壓
                "WS"	REAL, -- 風速
                "WD"	INTEGER, -- 風向
                "WSmax"	REAL, -- 最大風速
                "WDmax"	INTEGER, -- 最大風向
                "CloudAmount"	REAL, -- 總雲量
                "SunShineHour"	REAL, -- 日照時數
                "SunshineRate"	REAL, -- 日照率
                "GloblRad"	REAL, -- 全天空日射量
                "UVImax"	INTEGER, -- 最大紫外線
                PRIMARY KEY("sID","obs_date")
            );
        """
        self.sql_operate.create_table(syntax)

    # 爬取單一測站歷史觀測資料
    def crawler_history_obs(self, station, st, et):

        cm = arrow.now().floor("month")  # 取得當前月份
        cm = str(cm)

        url = f'https://codis.cwa.gov.tw/api/station?'

        payload = {
            'date': cm,
            'type': 'report_month',
            'stn_ID': station,
            'stn_type': 'cwb',
            # 'more': None,
            'start': st,
            'end': et
            # 'item': None
        }

        # 將表單資料轉換為URL編碼的字節串
        data = parse.urlencode(payload).encode('utf-8')

        # 計算Content-Length
        content_length = len(data)

        useragent = UserAgent().random
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Content-Length': str(content_length),
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Dnt': '1',
            'Host': 'codis.cwa.gov.tw',
            'Origin': 'https://codis.cwa.gov.tw',
            'Referer': 'https://codis.cwa.gov.tw/StationData',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': useragent,
            'X-Requested-With': 'XMLHttpRequest'
        }

        response = requests.post(url, headers=headers, data=data, timeout=5)

        while response.status_code != response.json()['code']:
            response = requests.post(
                url, headers=headers, data=data, timeout=5)

        data = response.json()['data'][0]['dts']
        history_obs = []

        # 寫入資料庫
        self.sql_operate.upsert(DataHistory, history_obs)

    # 初始化或更新資料庫
    def init_refresh_db(self):
        try:
            et = arrow.now().shift(days=-1).floor("day")  # 取得當前時間
            st = et.shift(days=-30).floor("day")  # 取得一個月前時間
            et = str(et).replace("+08:00", "")
            st = str(st).replace("+08:00", "")
            syntax = """
                SELECT *
                FROM station_list
                LIMIT 1
            """
            self.sql_operate.query(syntax)
            self.crawler_realtime_obs()

        except:
            et = arrow.now().shift(days=-1).floor("day")  # 取得當前時間
            st = et.shift(days=-366).floor("day")  # 取得一年前時間
            et = str(et).replace("+08:00", "")
            st = str(st).replace("+08:00", "")

            self.build_station_list()
            self.build_realtime_obs()
            self.build_history_obs()
            self.crawler_realtime_obs()
