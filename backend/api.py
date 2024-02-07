from typing import Optional
from fastapi import FastAPI
from backend.database import SqlOperate

sql_operate = SqlOperate()
app = FastAPI()  # 建立一個 Fast API application


@app.get("/")  # 指定 api 路徑 (get方法)
async def root():
    return {"message": "Hello World"}


@app.get("/realtime")  # 指定 api 路徑 (get方法)
async def weather_realtime():
    syntax = """
        SELECT s.id, s.name, s.alt, s.lng, s.lat, r.obs_time, r.Precp, r.WD, r.WS, r.Temperature, r.RH, r.UVI
        FROM station_list s JOIN data_realtime r
        ON s.id = r.id
    """
    data = sql_operate.query(syntax)
    return {"data": data}
