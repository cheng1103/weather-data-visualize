import streamlit as st
import datetime
import requests
import pandas as pd

# 疊圖
# https://vega.github.io/vega-lite/docs/layer.html

# 網頁標頭
st.set_page_config(
    page_title="歷史觀測資料",
    page_icon="📈",
    # menu_items={
    #     'About': ""
    # }
)


@st.cache_data
def get_stn_list():
    # 抓取測站清單
    response = requests.get('http://127.0.0.1:8000/stations')
    data = response.json()['data']
    stn_name_list = []

    for item in data:
        if item['state'] == 0:
            state = '(已裁撤)'
        else:
            state = ''
        stn = ' '.join([item['stn_name'], item['sID'], state])
        stn_name_list.append(stn)

    return stn_name_list


@st.cache_data
def get_stn_loc(stn_name):
    # 擷取觀測站位置資訊
    response = requests.get('http://localhost:8000/stations')
    data = response.json()['data']
    data = pd.DataFrame(data)
    stn_loc = data[data['stn_name'] == stn_name]
    stn_loc = stn_loc[['lon', 'lat']]
    return stn_loc


@st.cache_data
def get_history_data(stn_code, start_date, end_date):
    # 抓取單一測站歷史資料
    params = {
        'stn': stn_code,
        'start_date': start_date,
        'end_date': end_date,
    }
    response = requests.get('http://localhost:8000/history', params=params)
    data = response.json()['data']

    return data


# 邊欄部分
with st.sidebar:
    st.header('歷史觀測資料')  # 邊欄標題

    # 選取觀測站
    stn = st.selectbox('選取觀測站', get_stn_list())
    stn_name = stn.split(' ')[0]  # 擷取站名
    stn_code = stn.split(' ')[1]  # 擷取站碼

    time_start, time_end = st.columns(2)  # 欄位設定

    # 選擇資料起始日期
    with time_start:
        # 輸入日期
        start_date = st.date_input(
            '開始日期', value="today", min_value=datetime.date(1990, 1, 1))
        # 將日期轉為時間戳
        start_date_timestamp = datetime.datetime.strptime(
            str(start_date), "%Y-%m-%d").timestamp()
        start_date_timestamp = str(int(start_date_timestamp))

    # 選擇資料結束日期
    with time_end:
        # 輸入日期
        end_date = st.date_input(
            '結束日期', value="today", min_value=datetime.date(1990, 1, 1))
        # 將日期轉為時間戳
        end_date_timestamp = datetime.datetime.strptime(
            str(end_date), "%Y-%m-%d").timestamp()
        end_date_timestamp = str(int(end_date_timestamp))

    # 顯示設定的查詢條件
    st.write('觀測站：', stn_name)
    st.write('開始日期：', str(start_date))
    st.write('結束日期：', str(end_date))

    # 送出查詢條件
    if st.button('查詢資料'):
        data = get_history_data(
            stn_code, start_date_timestamp, end_date_timestamp)
        if len(data) == 0:
            st.text('查無資料，請重新查詢！')
        else:
            st.text('查詢成功！')
            data = pd.DataFrame(data)
            data['obs_date'] = pd.to_datetime(data['obs_date'], unit='s', utc=True).dt.tz_convert(
                'Asia/Taipei').dt.strftime('%Y-%m-%d')

    # 觀測站位置區塊
    st.divider()  # 分隔線
    st.subheader(f'{stn_name} 觀測站位置')
    st.map(get_stn_loc(stn_name), color='#00ff00', size=100)  # 用地圖顯示測站的所在地

# 主頁面部分
st.title(f'{stn_name} 觀測站歷史資料', anchor='頂端')  # 網頁標題
st.write('資料期間：', str(start_date), '~', str(end_date))
# 頁面標籤切換
trend, heatmap = st.tabs(["趨勢圖", "熱力圖"])

# 頁籤：趨勢圖
with trend:
    st.header('趨勢圖')
    with st.expander("快速導覽", expanded=True):
        st.markdown('[溫度變化](#溫度變化)')
        st.markdown('[雨量變化](#雨量變化)')
        st.markdown('[相對溼度變化](#相對溼度變化)')
        st.markdown('[風速變化](#風速變化)')

    st.subheader('溫度變化', anchor='溫度變化')
    try:
        trend_temperature = {
            # 'params': [
            #     {
            #         'name': 'grid',
            #         'select': 'interval',
            #         # 'bind': 'scales'
            #     }
            # ],
            'layer': [
                {
                    "mark": "line",  # 圖類型
                    "encoding": {
                        "x": {
                            "field": "obs_date",    # 引用資料的欄位名稱
                            "timeUnit": "binnedutcyearmonthdate",   # 時間單位
                            "type": "temporal",
                            "title": "日期",    # 坐標軸標題
                        },
                        "y": {
                            "field": "Temperature",
                            "type": "quantitative",
                            "title": "溫度(℃)",
                        },
                        "color": {"value": "orange"}    # 顏色設定
                    }
                },
                {
                    "mark": "rule",  # 圖類型
                    "encoding": {
                        "y": {
                            "aggregate": "mean",
                            "field": "Temperature",
                            "type": "quantitative",
                            # "title": "平均溫度(℃)"
                        },
                        "color": {"value": "red"},
                        "size": {"value": 2}
                    }
                }
            ]
        }
        st.vega_lite_chart(
            data, trend_temperature, theme="streamlit", use_container_width=True
        )

    except:
        st.text('無法顯示資料：\n1.您尚未送出查詢\n2.此查詢區間無任何資料\n3.本觀測站未提供此項資料')
    st.markdown('[⏫回快速導覽](#頂端)')

    st.subheader('雨量變化', anchor='雨量變化')
    try:
        trend_rainfall = {
            'layer': [
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {
                            "field": "obs_date",
                            "timeUnit": "binnedutcyearmonthdate",
                            "type": "temporal",
                            "title": "日期",
                        },
                        "y": {
                            "field": "Precp",
                            "type": "quantitative",
                            "title": "降雨量(mm)",
                        }
                    }
                },
                {
                    "mark": "rule",
                    "encoding": {
                        "y": {
                            "aggregate": "mean",
                            "field": "Precp",
                            "type": "quantitative",
                            # "title": "平均降雨量(mm)"
                        },
                        "color": {"value": "red"},
                        "size": {"value": 2}
                    }
                }
            ]
        }
        st.vega_lite_chart(
            data, trend_rainfall, theme="streamlit", use_container_width=True
        )

    except:
        st.text('無法顯示資料：\n1.您尚未送出查詢\n2.此查詢區間無任何資料\n3.本觀測站未提供此項資料')
    st.markdown('[⏫回快速導覽](#頂端)')

    st.subheader('相對溼度變化', anchor='相對溼度變化')
    try:
        trend_rainfall = {
            'layer': [
                {
                    "mark": "line",
                    "encoding": {
                        "x": {
                            "field": "obs_date",
                            "timeUnit": "binnedutcyearmonthdate",
                            "type": "temporal",
                            "title": "日期",
                        },
                        "y": {
                            "field": "RH",
                            "type": "quantitative",
                            "title": "相對濕度(%)",
                        },
                        "color": {"value": "lightblue"},
                    }
                },
                {
                    "mark": "rule",
                    "encoding": {
                        "y": {
                            "aggregate": "mean",
                            "field": "RH",
                            "type": "quantitative",
                            # "title": "平均相對濕度(%)"
                        },
                        "color": {"value": "red"},
                        "size": {"value": 2}
                    }
                }
            ]
        }

        st.vega_lite_chart(
            data, trend_rainfall, theme="streamlit", use_container_width=True
        )
    except:
        st.text('無法顯示資料：\n1.您尚未送出查詢\n2.此查詢區間無任何資料\n3.本觀測站未提供此項資料')
    st.markdown('[⏫回快速導覽](#頂端)')

    st.subheader('風速變化', anchor='風速變化')
    try:
        trend_rainfall = {
            'layer': [
                {
                    "mark": {
                        "type": "area",
                        "line": {
                            "color": "red"
                        },
                        "color": {
                            "x1": 1,
                            "y1": 1,
                            "x2": 1,
                            "y2": 0,
                            "gradient": "linear",
                            "stops": [
                                {
                                    "offset": 0,
                                    "color": "white"
                                },
                                {
                                    "offset": 1,
                                    "color": "red"
                                }
                            ]
                        }
                    },
                    "encoding": {
                        "x": {
                            "field": "obs_date",
                            "type": "temporal",
                            "title": "日期"
                        },
                        "y": {
                            "field": "WS",
                            "type": "quantitative",
                            "title": "平均風速(m/s)",
                        }
                    }
                },
                {
                    "mark": {
                        "type": "area",
                        "line": {
                            "color": "darkorange"
                        },
                        "color": {
                            "x1": 1,
                            "y1": 1,
                            "x2": 1,
                            "y2": 0,
                            "gradient": "linear",
                            "stops": [
                                {
                                    "offset": 0,
                                    "color": "white"
                                },
                                {
                                    "offset": 1,
                                    "color": "darkorange"
                                }
                            ]
                        }
                    },
                    "encoding": {
                        "x": {
                            "field": "obs_date",
                            "type": "temporal",
                            "title": "日期"
                        },
                        "y": {
                            "field": "WSmax",
                            "type": "quantitative",
                            "title": "最大風速(m/s)",
                        }
                    }
                },
            ]
        }

        st.vega_lite_chart(
            data, trend_rainfall, theme="streamlit", use_container_width=True
        )
    except:
        st.text('無法顯示資料：\n1.您尚未送出查詢\n2.此查詢區間無任何資料\n3.本觀測站未提供此項資料')
    st.markdown('[⏫回快速導覽](#頂端)')

# 頁籤：熱力圖
with heatmap:
    st.header('熱力圖')
    with st.expander("快速導覽", expanded=True):
        st.markdown('[氣溫熱力圖](#氣溫熱力)')
        st.markdown('[雨量熱力圖](#雨量熱力)')

    st.subheader('氣溫熱力圖', anchor='氣溫熱力')
    try:
        calendar_heatmap_temperature = {
            "mark": "rect",
            "encoding": {
                "x": {
                    "field": "obs_date",
                    "timeUnit": "date",
                    "type": "ordinal",
                    "title": "日",
                },
                "y": {
                    "field": "obs_date",
                    "timeUnit": "yearmonth",
                    "type": "ordinal",
                    "title": "年月"
                },
                "fill": {
                    "field": "Temperature",
                    "type": "quantitative",
                    "title": "溫度(℃)",
                    "scale": {"scheme": "redblue", "reverse": "True"}  # 填色條件
                },
            }
        }

        st.vega_lite_chart(
            data, calendar_heatmap_temperature, theme="streamlit", use_container_width=True
        )
    except:
        st.text('無法顯示資料：\n1.您尚未送出查詢\n2.此查詢區間無任何資料\n3.本觀測站未提供此項資料')
    st.markdown('[⏫回快速導覽](#頂端)')

    st.subheader('雨量熱力圖', anchor='雨量熱力')
    try:
        calendar_heatmap_rainfall = {
            "mark": "rect",
            "encoding": {
                "x": {
                    "field": "obs_date",
                    "timeUnit": "date",
                    "type": "ordinal",
                    "title": "日",
                },
                "y": {
                    "field": "obs_date",
                    "timeUnit": "yearmonth",
                    "type": "ordinal",
                    "title": "年月"
                },
                "fill": {
                    "field": "Precp",
                    "type": "quantitative",
                    "title": "降雨量(mm)",
                    "scale": {"scheme": "tealblues"}  # 填色條件
                },
            }
        }

        st.vega_lite_chart(
            data, calendar_heatmap_rainfall, theme="streamlit", use_container_width=True
        )
    except:
        st.text('無法顯示資料：\n1.您尚未送出查詢\n2.此查詢區間無任何資料\n3.本觀測站未提供此項資料')
    st.markdown('[⏫回快速導覽](#頂端)')
