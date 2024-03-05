# 主程式
import os

if __name__ == '__main__':

    # 主程式進入點
    command = f'streamlit run frontend/main.py  --server.port 8501 & uvicorn backend.main:app'
    os.system(command)
