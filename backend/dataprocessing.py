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


class SQLOperate:
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

    # 查詢資料(API)
    def api_query(self, syntax, syntax_params_dict):
        with Session(self.sqlite_engine) as session:
            query_result = session.execute(text(syntax), syntax_params_dict)
            query_data = query_result.fetchall()
            query_column_names = query_result.keys()

            result = [dict(zip(query_column_names, row)) for row in query_data]

        return result

    # 建立表格
    def create_table(self, syntax):
        with Session(self.sqlite_engine) as session:
            session.execute(text(syntax))
            session.commit()
            table_name = syntax.split('"')[1]
            print(f'資料表 {table_name} 建立成功！')

    # 新增或更新資料
    def upsert(self, table, data, batch_size=1000):
        # 取得資料表名稱
        tablename = table.__tablename__

        # 取得主鍵
        primary_key_columns = [
            column.name for column in table.__table__.columns if column.primary_key]

        # 取得更新資料的欄位
        set_dict = {}
        for key in data[0].keys():
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


class DataPipeline:
    '''
    資料處理
    '''

    def __init__(self) -> None:
        self.sql_operate = SQLOperate()

        # 讀取授權碼
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.cwa_authorization = config['cwa']['authorization']

        # 初始化連線物件
        self.session = requests.Session()
        retry = Retry(total=5, backoff_factor=3,
                      allowed_methods=frozenset(['GET', 'POST']))
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.keep_alive = False

    # 暫停
    def __pause(self, min_sec=0.5, max_sec=5):
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

    # 建立觀測站清單
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
                "start_date" TEXT, -- 設站日期
                "end_date" TEXT, -- 撤站日期
                "remark" TEXT, -- 備註
                "state" INTEGER, -- 狀態
                PRIMARY KEY("sID")
            );
        """
        self.sql_operate.create_table(syntax)

    # 更新現有觀測站清單
    def refresh_station_list(self):
        # 建構請求資料
        url = 'https://codis.cwa.gov.tw/api/station_list'
        useragent = UserAgent().random
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Dnt': '1',
            'Host': 'codis.cwa.gov.tw',
            'Referer': 'https://codis.cwa.gov.tw/StationData',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': useragent,
            'X-Requested-With': 'XMLHttpRequest'
        }

        # 爬取資料
        response = self.__web_requests_get(url, headers=headers)
        data = response.json()['data'][2]['item']

        station_list = []

        for item in data:
            if '雷達' not in item['stationName'] and len(item['address']) != 0:

                # 整理備註，若未填寫備註，則為None
                if len(item['webRemark']) != 0:
                    remark = item['webRemark']
                else:
                    remark = None

                # 整理撤站日期，若未撤站，則為撤站日期為None、state為1
                if len(item['stationEndDate']) == 0:
                    end_date = None
                    state = 1
                else:
                    end_date = item['stationEndDate']
                    state = 0

                station_list.append({
                    'sID': item['stationID'],
                    'stn_name': item['stationName'],
                    'alt': item['altitude'],
                    'lon': item['longitude'],
                    'lat': item['latitude'],
                    'county': item['countryName'],
                    'addr': item['address'],
                    'start_date': item['stationStartDate'],
                    'end_date': end_date,
                    'remark': remark,
                    'state': state
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

    # 爬取、並整理和寫入即時觀測資料
    def etl_realtime_obs(self):

        # 查詢現存測站代號
        syntax = """
            SELECT sID, stn_name 
            FROM station_list
            WHERE state = 1
        """
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
        def transform_realtime_obs(item):

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
            transform_realtime_obs, data, desc='資料整理進度')

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

    # 爬取、並整理和寫入所有測站歷史觀測資料
    def etl_history_obs(self, start_date, end_date):
        # 撈取觀測站清單
        syntax = """SELECT sID, stn_name FROM station_list"""
        # syntax = """
        #     SELECT sID, stn_name
        #     FROM station_list
        #     WHERE state = 1
        # """
        station_list = self.sql_operate.query(syntax)

        # 建立觀測站代碼轉換表
        station_list_code = {}
        for item in station_list:
            station_list_code[item['sID']] = item['stn_name']

        # 建構爬蟲所需的標頭與負載訊息
        def requests_params(item, st, et):
            cm = st.floor("month")  # 取得資料起始月份
            st = str(st.floor("day")).replace("+08:00", "")  # 轉換時間格式
            et = str(et.floor("day")).replace("+08:00", "")  # 轉換時間格式

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
                'Accept': 'application/json, text/javascript, */*; q=0.01',
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
                self.__pause(min_sec=0.75)
                response = self.session.post(
                    url, headers=headers, data=payload, timeout=5)

            except requests.exceptions.Timeout:
                self.__pause(min_sec=1.5)
                response = self.session.post(
                    url, headers=headers, data=payload, timeout=5)

            finally:
                if 'response' in locals():
                    while response.status_code != response.json()['code']:
                        self.__pause(min_sec=2)
                        response = self.session.post(
                            url, headers=headers, data=payload, timeout=5)
                else:
                    self.__pause(min_sec=2)
                    response = self.session.post(
                        url, headers=headers, data=payload, timeout=5)
                    while response.status_code != response.json()['code']:
                        self.__pause(min_sec=2)
                        response = self.session.post(
                            url, headers=headers, data=payload, timeout=5)

            self.session.close()

            try:
                data = response.json()['data'][0]
                data['stn_name'] = stn_name  # 將觀測站站名加入資料中
            except:
                data = None

            return data

        # 轉換並整理資料
        def transform_history_obs(item):
            histroy_obs = []
            stn_id = item['StationID']  # 觀測站代碼
            stn_name = item['stn_name']  # 觀測站名稱
            data = item['dts']

            for piece in data:

                # 轉換觀測日期格式
                obs_date = datetime.datetime.strptime(
                    piece['DataDate'], "%Y-%m-%dT%H:%M:%S").timestamp()
                obs_date = int(obs_date)

                # 整理氣壓相關資料：測站未提供此資料，則為None；儀器故障的部分改為None
                stn_pres = piece['StationPressure']['Mean']  # 測站氣壓
                sea_pres = piece['SeaLevelPressure']['Mean']  # 海平面氣壓
                if stn_pres == None or stn_pres < 0:
                    stn_pres = None
                if sea_pres == None or sea_pres < 0:
                    sea_pres = None

                # 整理相對濕度資料：測站未提供此資料，則為None；儀器故障的部分改為None
                rh = piece['RelativeHumidity']['Mean']
                if rh == None or rh < 0:
                    rh = None

                # 整理氣溫相關資料：測站未提供此資料，則為None；儀器故障的部分改為None
                temperature = piece['AirTemperature']['Mean']  # 單日平均氣溫
                t_max = piece['AirTemperature']['Maximum']  # 單日最高氣溫
                t_min = piece['AirTemperature']['Minimum']  # 單日最低氣溫
                if temperature == None or temperature == -99.5:
                    temperature = None
                if t_max == None or t_max == -99.5:
                    t_max = None
                if t_max == None or t_min == -99.5:
                    t_min = None

                # 整理風速相關資料：測站未提供此資料，則為None；儀器故障的部分改為None；風向未定則轉換為0
                ws = piece['WindSpeed']['Mean']  # 風速
                wd = piece['WindDirection']['Prevailing']  # 風向
                ws_max = piece['PeakGust']['Maximum']  # 最大瞬間風速
                wd_max = piece['PeakGust']['Direction']  # 最大瞬間風向
                if ws == None or ws < 0:
                    ws = None
                if wd == None or wd < 0:
                    wd = None
                elif wd > 360:
                    wd = 0
                if ws_max == None or ws_max < 0:
                    ws_max = None
                if wd_max == None or wd_max < 0:
                    wd_max = None
                elif wd_max > 360:
                    wd_max = 0

                # 降雨量：測站未提供此資料，則為None；儀器故障的部分改為None；轉換雨跡
                rainfall = piece['Precipitation']['Accumulation']  # 當日降雨量
                if rainfall != None:
                    if rainfall == -9.8:
                        rainfall = 0.05
                    elif rainfall < 0:
                        rainfall = None
                # 降雨時數：測站未提供此資料，則為None；儀器故障的部分改為None
                rainfall_length = piece['PrecipitationDuration']['Total']
                if rainfall_length == None or rainfall_length < 0:
                    rainfall_length = None

                # 整理日照資料：測站未提供此資料，則為None；儀器故障的部分改為None
                sunshine_hour = piece['SunshineDuration']['Total']  # 日照時數
                sunshine_rate = piece['SunshineDuration']['Rate']  # 日照率
                if sunshine_hour == None or sunshine_hour < 0:
                    sunshine_hour = None
                if sunshine_rate == None or sunshine_rate < 0:
                    sunshine_rate = None
                # 全天空日射量：測站未提供此資料，則為None；儀器故障的部分改為None
                globl_rad = piece['GlobalSolarRadiation']['Accumulation']
                if globl_rad == None or globl_rad < 0:
                    globl_rad = None

                # 整理最大紫外線資料：測站未提供此資料，則為None；儀器故障的部分改為None
                uvi_max = piece['UVIndex']['Maximum']
                if uvi_max == None or uvi_max < 0:
                    uvi_max == None

                # 整理總雲量資料：因濃霧無法觀察，定義為11
                cloud_amount = piece['TotalCloudAmount']['Mean']
                if cloud_amount == None:
                    cloud_amount == None
                elif cloud_amount < 0:
                    cloud_amount = 11

                histroy_obs.append({
                    'sID': stn_id,
                    'stn_name': stn_name,
                    'obs_date': obs_date,
                    'StnPres': stn_pres,  # 測站氣壓
                    'SeaPres': sea_pres,  # 海平面氣壓
                    'Temperature': temperature,  # 氣溫
                    'Tmax': t_max,  # 最高氣溫
                    'Tmin': t_min,  # 最低氣溫
                    'RH': rh,  # 相對溼度
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
        original_data_list = self.__multi_thread_task(
            web_requests_post, requests_list, desc='歷史觀測資料爬取進度')

        # 移除空缺元素
        data_list = [item for item in original_data_list if item != None]

        # 使用多線程處理資料
        data_bunchs = self.__multi_thread_task(
            transform_history_obs, data_list, desc='資料整理進度')

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

            # 若最新資料日期不是昨日，則更新
            if st != et:
                self.crawler_history_obs(st, et)

            # 更新即時資料
            self.crawler_realtime_obs()

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
