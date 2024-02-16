import logging
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
from functools import partial


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
        retry = Retry(total=5, backoff_factor=2,
                      allowed_methods=frozenset(['GET', 'POST']))
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.keep_alive = False

    # 暫停
    def __pause(self, min_sec=0.5, max_sec=2.5):
        t = random.uniform(min_sec, max_sec)
        time.sleep(t)

    """
    # 多工處理：使用多線程處理資料

    Args:
    - task: 處理每個資料項目的函式
    - data: 要處理的資料列表
    - max_workers: 同時運行的最大執行緒數量

    Returns:
    - 處理完成的結果列表
    """

    # 多工處理：使用多線程處理資料
    def __multi_thread_task(self, task, data, max_workers=4, desc=None):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交資料處理工作
            futures = [executor.submit(task, item) for item in data]
            # 使用tqdm追蹤進度
            results = [future.result()
                       for future in tqdm(futures, total=len(data), desc=desc)]

        return results

    # 多工處理：使用多線程處理資料
    # def __multi_thread_task(self, task, data,  max_workers=4):
    #     with ThreadPoolExecutor(max_workers=max_workers) as executor:
    #         # 提交資料處理工作
    #         futures = [executor.submit(task, item) for item in data]
    #         # 等待所有工作完成
    #         results = [future.result() for future in futures]

    #         return results

    # 發送請求(GET方法)
    def __web_requests_get(self, url, headers=None, params=None):

        try:
            self.__pause(min_sec=0.05)
            response = self.session.get(
                url, headers=headers, params=params, timeout=5)
        except:
            self.__pause(min_sec=0.5)
            response = self.session.get(
                url, headers=headers, params=params, timeout=5)
        finally:
            while response.status_code != requests.codes.ok:
                self.__pause(min_sec=1)
                response = self.session.get(
                    url, headers=headers, params=params, timeout=5)

        self.session.close()

        return response

    # 建立並爬取觀測站清單
    def build_station_list(self):
        syntax = """
            CREATE TABLE IF NOT EXISTS "station_list" (
                "sID"	TEXT, -- 測站代碼
                "stn_name"	TEXT, -- 測站名稱
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
        response = self.__web_requests_get(url, headers=headers)
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
                                     'stn_name': station_name_list[idx],
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
                "stn_name"	TEXT, -- 測站名稱
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
        syntax = """SELECT sID, stn_name FROM station_list"""
        station_list = self.sql_operate.query(syntax)

        stations = ''
        for item in station_list:
            stations = ','.join([stations, item['sID']])

        stations = stations[1:]

        # 建構請求資料
        params = {
            'Authorization': self.cwa_authorization,
            'StationId': stations,
            'WeatherElement': 'Now,WindDirection,WindSpeed,AirTemperature,RelativeHumidity,UVIndex',
            'GeoInfo': 'Coordinates'
        }

        # 爬取資料
        url = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001'
        response = self.__web_requests_get(url, params=params)

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
                'stn_name': item['StationName'],
                'obs_time': obs_time,
                'Precp': rainfall,
                'WD': weather_element['WindDirection'],
                'WS': weather_element['WindSpeed'],
                'Temperature': weather_element['AirTemperature'],
                'RH': weather_element['RelativeHumidity'],
                'UVI': weather_element['UVIndex']
            }
        # 使用多線程處理資料
        process_result = self.__multi_thread_task(
            extract_realtime_obs, data, desc='資料整理進度')

        # 寫入資料庫
        self.sql_operate.upsert(DataRealtime, process_result)

    # 建立歷史觀測資料表
    def build_history_obs(self):
        syntax = """
            CREATE TABLE IF NOT EXISTS "data_history" (
                "sID"	TEXT, -- 測站代碼
                "stn_name"	TEXT, -- 測站名稱
                "obs_date"	INTEGER, -- 資料日期
                "StnPres"	REAL, -- 測站氣壓
                "SeaPres"	REAL, -- 海平面氣壓
                "Temperature"	REAL, -- 氣溫
                "Tmax"	REAL, -- 最高氣溫
                "Tmin"	REAL, -- 最低氣溫
                "RH"	REAL, -- 相對溼度
                "WS"	REAL, -- 風速
                "WD"	INTEGER, -- 風向
                "WSmax"	REAL, -- 最大風速
                "WDmax"	INTEGER, -- 最大風向
                "Precp"	REAL, -- 降雨量
                "PrecpHour"	REAL, -- 降雨時數 
                "SunShineHour"	REAL, -- 日照時數
                "SunshineRate"	REAL, -- 日照率
                "GloblRad"	REAL, -- 全天空日射量
                "VisbMean"	REAL, -- 能見度
                "UVImax"	REAL, -- 最大紫外線
                "CloudAmount"	REAL, -- 總雲量
                PRIMARY KEY("sID","obs_date")
            );
        """
        self.sql_operate.create_table(syntax)

    # 爬取所有測站歷史觀測資料
    def crawler_history_obs(self, start_date, end_date):
        # 撈取觀測站清單
        syntax = """SELECT sID, stn_name FROM station_list"""
        station_list = self.sql_operate.query(syntax)

        # 建立觀測站代碼轉換表
        station_list_code = {}
        for item in station_list:
            station_list_code[item['sID']] = item['stn_name']

        # 建構爬蟲所需的標頭與負載訊息
        def requests_params(item, st, et):
            cm = arrow.now().floor("month")  # 取得當前月份

            # 建構表單資料
            payload = {
                'date': str(cm),
                'type': 'report_month',
                'stn_ID': item['sID'],
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

            # 建構標頭
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

            return (headers, payload, item['stn_name'])

        # 發送請求(POST方法)
        def web_requests_post(item):
            headers = item[0]  # 帶入標頭
            payload = item[1]  # 帶入負載訊息
            stn_name = item[2]  # 取得觀測站站名

            url = f'https://codis.cwa.gov.tw/api/station?'

            try:
                self.__pause(min_sec=0.5)
                response = self.session.post(
                    url, headers=headers, data=payload, timeout=5)

            except:
                self.__pause(min_sec=1)
                response = self.session.post(
                    url, headers=headers, data=payload, timeout=5)

            finally:
                while response.status_code != response.json()['code']:
                    self.__pause(min_sec=1.5)
                    response = self.session.post(
                        url, headers=headers, data=payload, timeout=5)

            self.session.close()

            data = response.json()['data'][0]
            data['stn_name'] = stn_name  # 將觀測站站名加入資料中

            return data

        # 轉換並整理資料
        def extract_history_obs(item):
            histroy_obs = []
            stn_id = item['StationID']  # 觀測站代碼
            stn_name = item['stn_name']  # 觀測站名稱
            data = item['dts']

            for piece in data:

                # 轉換觀測日期格式
                obs_date = datetime.datetime.strptime(
                    piece['DataDate'], "%Y-%m-%dT%H:%M:%S").timestamp()
                obs_date = int(obs_date)

                # 整理氣壓相關資料：儀器故障的部分改為None
                stn_pres = piece['StationPressure']['Mean']  # 測站氣壓
                sea_pres = piece['SeaLevelPressure']['Mean']  # 海平面氣壓
                if stn_pres < 0:
                    stn_pres = None
                if sea_pres < 0:
                    sea_pres = None

                # 整理氣溫相關資料：儀器故障的部分改為None
                t_max = piece['AirTemperature']['Maximum']  # 最高氣溫
                t_min = piece['AirTemperature']['Minimum']  # 最低氣溫
                if t_max == -99.5:
                    t_max = None
                if t_min == -99.5:
                    t_min = None

                # 整理風速相關資料：儀器故障的部分改為None
                ws = piece['WindSpeed']['Mean']  # 風速
                wd = piece['WindDirection']['Prevailing']  # 風向
                ws_max = piece['PeakGust']['Maximum']  # 最大瞬間風速
                wd_max = piece['PeakGust']['Direction']  # 最大瞬間風向
                if ws < 0:
                    ws = None
                if wd < 0:
                    wd = None
                if ws_max < 0:
                    ws_max = None
                if wd_max < 0:
                    wd_max = None

                # 整理雨量相關資料：轉換雨跡、降雨時數故障紀錄的部分改為None
                rainfall = piece['Precipitation']['Accumulation']  # 當日降雨量
                # 降雨時數
                rainfall_length = piece['PrecipitationDuration']['Total']
                if rainfall < 0:
                    rainfall = 0.25
                if rainfall_length < 0:
                    rainfall_length = None

                # 整理日照資料：儀器故障的部分改為None
                sunshine_hour = piece['SunshineDuration']['Total']  # 日照時數
                sunshine_rate = piece['SunshineDuration']['Rate']  # 日照率
                # 全天空日射量
                globl_rad = piece['GlobalSolarRadiation']['Accumulation']
                if sunshine_hour < 0:
                    sunshine_hour = None
                if sunshine_rate < 0:
                    sunshine_rate = None
                if globl_rad < 0:
                    globl_rad = None

                # 整理最大紫外線資料：儀器故障的部分改為None
                uvi_max = piece['UVIndex']['Maximum']
                if uvi_max != None:
                    if uvi_max < 0:
                        uvi_max = None

                # 整理總雲量資料：因濃霧無法觀察，定義為11
                cloud_amount = piece['TotalCloudAmount']['Mean']
                if cloud_amount != None:
                    if cloud_amount < 0:
                        cloud_amount = 11

                histroy_obs.append({
                    'sID': stn_id,
                    'stn_name': stn_name,
                    'obs_date': obs_date,
                    'StnPres': stn_pres,  # 測站氣壓
                    'SeaPres': sea_pres,  # 海平面氣壓
                    'Temperature': piece['AirTemperature']['Mean'],  # 氣溫
                    'Tmax': t_max,  # 最高氣溫
                    'Tmin': t_min,  # 最低氣溫
                    'RH': piece['RelativeHumidity']['Mean'],  # 相對溼度
                    'WS': ws,  # 風速
                    'WD': wd,  # 風向
                    'WSmax': ws_max,  # 最大瞬間風速
                    'WDmax': wd_max,  # 最大瞬間風向
                    'Precp': rainfall,  # 當日降雨量
                    'PrecpHour': rainfall_length,  # 降雨時數
                    'SunShineHour': sunshine_hour,  # 日照時數
                    'SunshineRate': sunshine_rate,  # 日照率
                    'GloblRad': globl_rad,  # 全天空日射量
                    'VisbMean': piece['Visibility']['Mean'],  # 能見度
                    'UVImax': uvi_max,  # 最大紫外線
                    'CloudAmount': cloud_amount  # 總雲量
                })

            return histroy_obs

        # 生成爬蟲所需的資料清單
        requests_list = list(
            map(partial(requests_params, st=start_date, et=end_date), station_list))

        # 使用多線程爬蟲與初步處理資料
        data_list = self.__multi_thread_task(
            web_requests_post, requests_list, desc='歷史觀測資料爬取進度')

        # 使用多線程處理資料
        data_bunchs = self.__multi_thread_task(
            extract_history_obs, data_list, desc='資料整理進度')
        # 將多個list合併為一串列
        data = [element for item in data_bunchs for element in item]

        # 按測站代號升序，再日期升序
        data = sorted(data, key=lambda item: (item['sID']))
        data = sorted(data, key=lambda item: (item['obs_date']))

        # 寫入資料庫
        self.sql_operate.upsert(DataHistory, data)

    # 初始化或更新資料庫
    def init_refresh_db(self):
        # 更新
        try:
            # 取得資料庫最新資料的日期
            syntax = """SELECT obs_date FROM data_history ORDER BY obs_date DESC LIMIT 1"""
            st = self.sql_operate.query(syntax)[0]['obs_date']
            st = datetime.datetime.fromtimestamp(
                st).strftime('%Y-%m-%dT%H:%M:%S')

            # 取得前一日時間
            et = arrow.now().shift(days=-1).floor("day")
            et = str(et).replace("+08:00", "")

            # 更新所有資料
            self.crawler_realtime_obs()
            self.crawler_history_obs(st, et)

        # 初始化
        except:
            et = arrow.now().shift(days=-1).floor("day")  # 取得前一日時間
            st = et.shift(days=-366).floor("day")  # 取得一年前時間
            et = str(et).replace("+08:00", "")
            st = str(st).replace("+08:00", "")

            self.build_station_list()
            self.build_realtime_obs()
            self.crawler_realtime_obs()
            self.build_history_obs()
            self.crawler_history_obs(st, et)
