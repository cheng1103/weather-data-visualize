# Weather data visualize 氣象資料視覺化
![Static Badge](https://img.shields.io/badge/Python-3.8.10-blue)
![Static Badge](https://img.shields.io/badge/FastAPI-0.109.0-green)
![Static Badge](https://img.shields.io/badge/Streamlit-1.30.0-red)

## 大綱
- [使用限制](#使用限制)
- [開始使用](#開始使用)
- [功能簡介](#功能簡介)
- [操作示範](#操作示範)
- [專案目錄](#專案目錄)
- [執行環境要求](#執行環境要求)
- [安裝與執行](#安裝與執行)
- [資料來源](#資料來源)
- [參考資料](#參考資料)

## 使用限制
__《！！重要！！》本專案是部署在免費版的Render上，每當超過15分鐘無任何人使用時，會進入休眠狀態，喚醒時需等待2~3分鐘，接著即可正常使用。__

[⏫回大綱](#大綱)


## 開始使用
掃描以下QRcode，或是 __[點擊我](https://weather-data-visualize.onrender.com/)__ 開啟網頁

![QRcode](assets/qrcode.png)

[⏫回大綱](#大綱)


## 操作示範

[⏫回大綱](#大綱)


## 專案目錄
```
.
+-- assets      # 包含 gif、png 等素材圖檔
+-- backend
|   +-- main.py # FastAPI的主程式
|   +-- dataprocessing.py   # 資料庫操作和資料處理管線
|   +-- models.py	# 資料表模型
|   
|
+-- frontend
|   +-- main    # 主頁面
|   +-- pages 
|       +-- history.py  # 歷史資料頁面  
|       +-- realtime.py # 即時資料頁面
|
+-- data
|   +-- weather.db # 氣象資料庫
|
+-- requirements.txt	# 相依套件
+-- example_config.ini  # 設定檔範例
+-- README.md	# 說明文件
```
[⏫回大綱](#大綱)


## 執行環境要求
* 硬體最低要求：CPU至少要有 4個執行緒
* 套件要求詳見 [requirements.txt](requirements.txt)

[⏫回大綱](#大綱)


## 安裝與執行
### 申請氣象資料開放平台授權碼 （若已申請，可忽略此步驟）
1. 請至中央氣象署填寫資料[加入會員](https://pweb.cwa.gov.tw/emember/register/authorization)
2. [登入會員](https://opendata.cwa.gov.tw/userLogin)後，[進入頁面](https://opendata.cwa.gov.tw/user/authkey)，點擊「__取得授權碼__」。
![cwa opendata authorization](assets/cwa_opendata_authorization.png)
3. 將 __example_config.ini__ 中的 __your_cwa_authorization__ ，取代為您的授權碼
4. 再把「 __example_config.ini__ 」的檔名，修改為 「 __config.ini__ 」
### 本地端執行
1. 移至 __config讀取授權碼__ 的註解處，將以下程式碼 __移除註解__：
```shell
    config = configparser.ConfigParser()
    config.read('config.ini')
    self.cwa_authorization = config['cwa']['authorization']
```
2. 接著為以下程式 __加入註解__：
```shell
    self.cwa_authorization = os.environ.get("CWA_AUTHORIZATION")
```
3. 最後在命令列中下達指令：`python main.py` ，即可在本機上操作！
### Render部署
1. 進入 Render 頁面，點選右上角 __「New」__ 的 __「Web Service」__，接著在 __「Public Git repository」__ 中貼上本專案的[網址](https://github.com/cheng1103/weather-data-visualize)，然後點選 __Continue__
2. 在 __「Name」__ 填入自訂名稱(同時是網站名稱)，還有在 __「Start Command」__ 填入`python main.py`
3. 接著在 __「Environment Variables」__ 填入環境變數名稱： __CWA_AUTHORIZATION__ ，以及你的 __氣象資料開放平台授權碼__ (重要)
4. 最後點選 __「Create Web Service」__ ，即可完成部署了！

[⏫回大綱](#大綱)


## 資料來源
1. [中央氣象署](https://www.cwa.gov.tw/)
2. [氣象資料開放平台](https://opendata.cwa.gov.tw/)
3. [氣候資料服務系統](https://codis.cwa.gov.tw/)

[⏫回大綱](#大綱)


## 參考資料
1. [SQLAlchemy文檔](https://www.osgeo.cn/sqlalchemy/)
2. [SQLAlchemy中的text對象防注入](https://www.cnblogs.com/qijunL/articles/15740080.html)
3. [SQLAlchemy執行原生sql防止sql注入](https://www.jianshu.com/p/f78a4edacdb2)
4. [FastAPI](https://fastapi.tiangolo.com/zh-hant/)
5. [Fast API 入門筆記](https://minglunwu.com/tags/fast-api-tutorial/)
6. [菜鳥教學 - Python map() 函數](https://www.runoob.com/python/python-func-map.html)
7. [菜鳥教學 - Python按鍵(key)或value(value)對字典進行排序](https://www.runoob.com/python3/python-sort-dictionaries-by-key-or-value.html)
8. [[Python] 使用 functools.partial() 固定函式參數並返回新的 partial 物件](https://clay-atlas.com/blog/2023/03/19/python-functools-partial-function/)
9. [STEAM 教育學習網 - concurrent.futures 平行任務處理](https://steam.oxxostudio.tw/category/python/library/concurrent-futures.html)
10. [STEAM 教育學習網 - 爬取後同時下載多張圖片](https://steam.oxxostudio.tw/category/python/spider/ptt-more-images.html)
11. [Learn Code With Mike - [Python爬蟲教學]善用多執行緒(Multithreading)提升Python網頁爬蟲的執行效率](https://www.learncodewithmike.com/2020/11/multithreading-with-python-web-scraping.html)
12. [Streamlit • A faster way to build and share data apps](https://streamlit.io/)
13. [TEJ API 遇上STREAMLIT App](https://www.tejwin.com/insight/tej-api-%E9%81%87%E4%B8%8Astreamlit-app/)
14. [Streamlit🔥+ FastAPI⚡️- The ingredients you need for your next Data Science Recipe](https://medium.com/codex/streamlit-fastapi-%EF%B8%8F-the-ingredients-you-need-for-your-next-data-science-recipe-ffbeb5f76a92)
15. [Vega-Lite – A Grammar of Interactive Graphics](https://vega.github.io/vega-lite/)


[⏫回大綱](#大綱)