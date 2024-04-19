import streamlit as st

# 網頁標頭
st.set_page_config(
    page_title="氣象資料視覺化",
    page_icon="🌦",
    # menu_items={
    #     'About': ""
    # }
)

# add_page_title()

# 邊欄部分
with st.sidebar:
    st.title('氣象資料視覺化')  # 邊欄標題

# 主頁面部分
st.header('氣象資料視覺化')  # 網頁標題

# 主頁面內容
content = '''本專案是藉由氣象署所提供的公開資料，透過資料視覺化，展示氣象的長期趨勢，以及藉由地圖掌握即時天氣概況。

- 專案架構：
1. 前端介面：**[Streamlit](https://streamlit.io/ "Streamlit - A faster way to build and share data apps")**(由Python構成)
2. 後端架構：**FastAPI**、**SQLAlchemy**
3. 資料庫：**SQLite**

- 使用技術：
 1. 爬蟲：加入反爬蟲機制，例如User-Agent/延遲時間/Session，提高爬取成功率。
 2. 平行處理：加快爬蟲速度、縮短資料整理時間。
 3. 防止SQL注入攻擊：避免資料庫遭到惡意攻擊，而使資料庫被清空。

- 功能簡介：
 1. 歷史趨勢(history)：查閱各測站的天氣變化，資料期間為 **1990/01/01 ~ 2024/04/19** 。
 2. 即時天氣(realtime)：以地圖呈現各地天氣概況。
'''

st.markdown(content)

st.markdown('- 操作示範：')
st.markdown('  1. 歷史趨勢圖')
st.html('<p><img src="https://raw.githubusercontent.com/cheng1103/weather-data-visualize/main/assets/demo_history.gif" width="80%"></p>')
st.markdown('  2. 即時天氣圖')
st.html('<p><img src="https://raw.githubusercontent.com/cheng1103/weather-data-visualize/main/assets/demo_realtime.gif" width="80%"></p>')

# - 操作示範：

#   * 歷史趨勢圖

# <p><img src="https://raw.githubusercontent.com/cheng1103/weather-data-visualize/main/assets/demo_history.gif" width="80%"></p>

#   * 即時天氣圖

# <p><img src="https://raw.githubusercontent.com/cheng1103/weather-data-visualize/main/assets/demo_realtime.gif" width="80%"></p>
