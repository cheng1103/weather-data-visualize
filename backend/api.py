from typing import Optional
from fastapi import FastAPI
from backend.database import *

sql_operate = SqlOperate()
data_pipeline = DataPipeline()
app = FastAPI()  # 建立一個 Fast API application


@app.get("/")
# 根目錄
async def root():
    return {"message": "Hello World"}


@app.get("/realtime")
# 回傳觀測資料
async def weather_data_realtime():
    syntax = """
        SELECT s.sID, s.stn_name, s.alt, s.lon, s.lat, r.obs_time, r.Precp, r.WD, r.WS, r.Temperature, r.RH, r.UVI
        FROM station_list s JOIN data_realtime r
        ON s.sID = r.sID
    """
    data = sql_operate.query(syntax)
    return {"data": data}


@app.post("/realtime")
# 更新目前觀測資料
async def weather_realtime_data_refresh():
    data_pipeline.crawler_realtime_obs()
    return {"message": "Refresh successful!"}


@app.get("/history")
# 回傳歷史資料
async def weather_data_history(stn: str, start: int, end: int):
    syntax = """
        SELECT s.sID, s.stn_name, s.alt, s.lon, s.lat, h.obs_date, h.Precp, h.WD, h.WS, h.Temperature, h.RH, h.UVImax
        FROM station_list s JOIN data_history h
        ON s.sID = h.sID
        WHERE h.stn_name = :stn
        AND h."obs_date" BETWEEN :start AND :end
    """
    syntax_params = {
        'stn': stn,
        'start': start,
        'end': end,
    }
    data = sql_operate.api_query(syntax, syntax_params)
    return {"data": data}
