import streamlit as st

st.set_page_config(
    page_title="氣象資料視覺化",
    page_icon="🌦",
    # menu_items={
    #     'About': ""
    # }
)


# st.markdown("主頁面")
# st.sidebar.write("主頁") #邊欄


# add_page_title()

# 邊欄
with st.sidebar:
    st.title('首頁')  # 邊欄標題

st.header('首頁')
