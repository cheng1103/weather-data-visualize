import streamlit as st
import requests
import pandas as pd
import pydeck as pdk

# 網頁標頭
st.set_page_config(
    page_title="即時天氣圖資",
    page_icon="⏱",
    # menu_items={
    #     'About': ""
    # }
)


@st.cache_data
def get_realtime_data():
    # 抓取即時觀測資料
    response = requests.get('http://localhost:8000/realtime')
    data = pd.DataFrame(response.json()['data'])
    data['obs_time'] = pd.to_datetime(data['obs_time'], unit='s', utc=True).dt.tz_convert(
        'Asia/Taipei').dt.strftime('%Y-%m-%d %H:%M:%S')
    # data.rename(columns={'Temperature': 'temp'}, inplace=True)

    return data


# 邊欄部分
with st.sidebar:
    st.header('即時天氣圖資')  # 邊欄標題

# 主頁面部分
st.title('即時天氣圖資')  # 網頁標題

data = get_realtime_data()

st.write('資料時間：', str(data['obs_time'][0]))  # 無法更新資料時間

if st.button('更新資料'):  # 更新按鈕
    with st.status("資料更新中……") as status:  # 顯示更新狀態
        requests.put('http://localhost:8000/realtime')
        st.write("資料更新中……")
        status.update(label="更新完成！", state="complete")
        st.write("更新完成！")
        # data = get_realtime_data()

# 頁面標籤切換
temperature, rainfall = st.tabs(["氣溫", "雨量"])


with temperature:
    st.header('目前溫度分布')
    st.text('建置中，目前不提供資料！')

    # 設定地圖參數
    view_state = pdk.data_utils.compute_view(data[['lon', 'lat']])
    view_state.bearing = 0  # 指向正北
    view_state.zoom = 6.25  # 地圖預設縮放大小
    view_state.pitch = 0  # 俯視角度

    color_scheme = f"""[
        49.8374 + 11.0957 * temp - 0.04 *temp * temp - 0.00343 * temp * temp * temp, 
        94.0929 + 13.9894 * temp - 0.2576 * temp * temp - 0.00309 * temp * temp * temp, 
        96.4520 + 24.6847 * temp - 1.2077 *temp * temp + 0.0139 * temp * temp * temp
        ]"""

    layer = [
        pdk.Layer(type='ColumnLayer',
                  data=data,
                  get_position='[lon, lat]',
                  radius=100,
                  auto_highlight=True,
                  pickable=True,
                  get_fill_color=color_scheme,
                  coverage=1),
    ]

    st.pydeck_chart(
        pdk.Deck(
            map_style=None,
            initial_view_state=view_state,
            layers=layer,
            # tooltip=tooltip,
        )
    )


with rainfall:
    st.header('本日累積雨量')
    st.text('維護中，資料僅供參考！')

    # 設定地圖參數
    view_state = pdk.data_utils.compute_view(data[['lon', 'lat']])
    view_state.bearing = 0  # 指向正北
    view_state.zoom = 6.25  # 地圖預設縮放大小
    view_state.pitch = 45  # 俯視角度

    layer = [
        pdk.Layer(type='ColumnLayer',
                  data=data,
                  get_position='[lon, lat]',
                  get_elevation='Precp',
                  get_radius=100,
                  auto_highlight=True,
                  elevationScale=1000,
                  pickable=True,
                  extruded=True,
                  get_fill_color=['Precp', 255],
                  coverage=2),
    ]

    st.pydeck_chart(
        pdk.Deck(
            map_style=None,
            initial_view_state=view_state,
            layers=layer
        )
    )
