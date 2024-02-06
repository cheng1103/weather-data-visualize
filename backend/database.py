from tqdm import tqdm
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Session, sessionmaker


class SqlOperate:
    def __init__(self) -> None:
        DATABASE_URL = f"sqlite:///data/weather.db"
        self.sqlite_engine = create_engine(DATABASE_URL)

    # 查詢資料
    def query(self, syntax):
        with Session(self.sqlite_engine) as session:
            result = session.execute(text(syntax))
            data = result.fetchall()
            column_names = result.keys()

            query_result = [dict(zip(column_names, row)) for row in data]

        return query_result

    # 建立表格
    def create_table(self, syntax):
        with Session(self.sqlite_engine) as session:
            session.execute(text(syntax))
            session.commit()
            table_name = syntax.split('"')[1]
            print(f'資料表 {table_name} 建立成功！')

    # 新增或更新資料
    def upsert(self, table, data, batch_size=10000):
        # 取得主鍵
        primary_key_columns = [
            column.name for column in table.__table__.columns if column.primary_key]

        # 取得更新資料的欄位
        set_dict = {}
        for key, value in data[0].items():
            if key not in primary_key_columns:
                set_dict[key] = getattr(sqlite.insert(table).excluded, key)

        # 將資料分割為多個批次
        batches = []
        for idx in range(0, len(data), batch_size):
            batch = data[idx: idx + batch_size]
            batches.append(batch)

        # 批次新增或更新資料
        with Session(self.sqlite_engine) as session:
            session.begin()

            try:
                for batch_data in tqdm(batches, desc='資料寫入進度'):
                    insert_stmt = sqlite.insert(table).values(batch_data)
                    on_conflict_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=primary_key_columns, set_=set_dict)

                    session.execute(on_conflict_stmt)
                session.commit()

            except Exception as e:
                session.rollback()
                print(e)
