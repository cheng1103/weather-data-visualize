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
async def weather_realtime():
    syntax = """
        SELECT s.id, s.name, s.alt, s.lon, s.lat, r.obs_time, r.Precp, r.WD, r.WS, r.Temperature, r.RH, r.UVI
        FROM station_list s JOIN data_realtime r
        ON s.id = r.id
    """
    data = sql_operate.query(syntax)
    return {"data": data}


@app.post("/realtime")
# 更新目前觀測資料
async def weather_realtime_refresh():
    data_pipeline.crawler_realtime_obs()
    return {"message": "Refresh successful!"}
