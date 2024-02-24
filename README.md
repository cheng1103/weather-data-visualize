# Weather data visualize 氣象資料視覺化
![Static Badge](https://img.shields.io/badge/Python-3.8.10-blue)

## 大綱
- [開始使用](#開始使用)
- [功能](#功能)
- [操作示範](#操作示範)
- [專案目錄](#專案目錄)
- [執行環境要求](#執行環境要求)
- [安裝與執行](#安裝與執行)
- [資料來源](#資料來源)
- [參考資料](#參考資料)


## 開始使用

[⏫回大綱](#大綱)


## 專案目錄
```
.
+-- assets      # 包含 gif、png 等素材圖檔
+-- backend
|   +-- api.py # 
|   +-- database.py # 
|   +-- models.py #  
|   +-- # 
|
+-- frontend
|   +-- # 
|   +-- pages 
|       +-- #  
|       +-- #
|
+-- data
|   +-- weather.db # 氣象資料庫
|
|
+-- #
+-- #
+-- #
+-- requirements.txt  # 相依套件
+-- example_config.ini  # 設定檔範例
+-- README.md  # 說明文件
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
13. [Streamlit🔥+ FastAPI⚡️- The ingredients you need for your next Data Science Recipe](https://medium.com/codex/streamlit-fastapi-%EF%B8%8F-the-ingredients-you-need-for-your-next-data-science-recipe-ffbeb5f76a92)
14. [Vega-Lite – A Grammar of Interactive Graphics](https://vega.github.io/vega-lite/)


[⏫回大綱](#大綱)