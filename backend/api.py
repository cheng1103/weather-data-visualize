from typing import Optional
from fastapi import FastAPI
from backend.database import SqlOperate

sql_operate = SqlOperate()
app = FastAPI()  # 建立一個 Fast API application


@app.get("/")  # 指定 api 路徑 (get方法)
async def root():
    return {"message": "Hello World"}


@app.get("/realtime")  # 指定 api 路徑 (get方法)
async def realtime_weather():
    syntax = """
        SELECT *
        FROM data_realtime
    """
    data = sql_operate.query(syntax)
    return {"data": data}
