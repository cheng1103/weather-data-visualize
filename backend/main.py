from typing import Optional
from fastapi import FastAPI
from backend.dataprocessing import *

sql_operate = SQLOperate()
data_pipeline = DataPipeline()
app = FastAPI()  # 建立一個 Fast API application


@app.get("/")
# 根目錄
async def root():
    return {"message": "Hi! Here is the backend for meteorological observation data."}


@app.get("/stations")
# 回傳觀測站清單
async def station_list():
    """
    取得所有觀測站
    """

    syntax = """
        SELECT sID, stn_name, lon, lat, state
        FROM station_list
    """
    data = sql_operate.query(syntax)
    return {"data": data}


@app.get("/realtime")
# 回傳觀測資料
async def weather_realtime_data():
    """
    回傳現存觀測站的觀測資料
    """

    syntax = """
        SELECT s.sID, s.stn_name, s.alt, s.lon, s.lat, r.obs_time, r.Precp, r.WD, r.WS, r.Temperature, r.RH, r.UVI
        FROM station_list s JOIN data_realtime r
        ON s.sID = r.sID
        WHERE s.state = 1
    """
    data = sql_operate.query(syntax)
    return {"data": data}


@app.put("/realtime")
# 更新目前觀測資料
async def weather_realtime_data_update():
    """
    更新現存觀測站的觀測資料
    """

    data_pipeline.etl_realtime_obs()
    return {"message": "Refresh successful!"}


@app.head("/history")
# 更新歷史觀測資料
async def weather_historical_data_update():
    """
    更新所有觀測站的歷史觀測資料
    """

    data_pipeline.update_historical_data()
    return {"message": "Refresh successful!"}


@app.get("/history")
# 回傳單一測站之歷史資料
async def weather_historical_data(stn: str, start_date: int, end_date: int):
    """
    查詢所有觀測站指定期間內的觀測資料

    - 輸入：
    1. stn：觀測站代碼
    2. start_date：查詢起始日期(格式為時間戳)
    3. end_date：查詢結束日期(格式為時間戳)
    """

    syntax = """
        SELECT obs_date, Precp, WS, WSmax, Temperature, RH, UVImax
        FROM data_history
        WHERE sID = :stn
        AND obs_date BETWEEN :start AND :end
    """
    syntax_params = {
        'stn': stn,
        'start': start_date,
        'end': end_date,
    }
    data = sql_operate.api_query(syntax, syntax_params)
    return {"data": data}


@app.get("/history_multi", response_description="開發中", deprecated=True)
# 回傳多個測站之歷史資料
async def weather_historical_data(stns: str, start: int, end: int):
    """
    回傳多個測站之歷史資料

    """

    syntax = """
        SELECT obs_date, Precp, WD, WS, Temperature, RH, UVImax
        FROM data_history
        WHERE sID IN :stns
        AND obs_date BETWEEN :start AND :end
    """
    syntax_params = {
        'stns': stns,
        'start': start,
        'end': end,
    }
    data = sql_operate.api_query(syntax, syntax_params)
    return {"data": data}
