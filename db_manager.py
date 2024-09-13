from sqlalchemy import create_engine, Column, String, Integer, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, exists, update
import sqlalchemy
from datetime import datetime, timezone
import os
from dotenv import load_dotenv



load_dotenv()

#подгружаем базу данных
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
port = os.getenv('DB_PORT')
database = os.getenv('DB_DATABASE')

DATABASE_URL = f'postgresql://{username}:{password}@{host}:{port}/{database}'

# Создание базы данных и настройка SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()
Base = sqlalchemy.orm.declarative_base()


# Определение модели для таблицы user_records
class User(Base):
    __tablename__ = 'user_records'
    
    user_id = Column(String, primary_key=True)
    thread_id = Column(String)

#Определение модели для таблицы tokens
class Tokens(Base):
    __tablename__ = 'tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String)
    thread_id = Column(String)
    prompt_tokens = Column(String)
    completion_tokens = Column(String)
    total_tokens = Column(String)
    model = Column(String)
    date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    time = Column(Time, default=lambda: datetime.now(timezone.utc).time())


# Менеджер базы данных
class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self.Session = Session

    def create_tables(self):
        """Создаем таблицы"""
        Base.metadata.create_all(self.engine)

    def add_user(self, user_id, thread_id):
        """Добавляем пользователя"""
        session = self.Session()
        new_user = User(user_id=user_id, thread_id=thread_id)
        session.add(new_user)
        session.commit()
        session.close()

    def update_user(self, user_id, thread_id):
        """Замена старого thread_id на новый"""
        session = self.Session()
        # Выполнение запроса на обновление
        session.query(User).filter(User.user_id == user_id).update({
            User.thread_id: thread_id
        })
        # Сохранение изменений в базе данных
        session.commit()

    def exists(self, user_id, thread_id):
        """Проверка существования ыук_шв"""
        exists_query = session.query(exists().where(User.user_id == user_id)).scalar()
        return exists_query
    
    def add_tokens(self, user_id, thread_id, prompt_tokens, completion_tokens, total_tokens,model):
        """Добавляем информацию о токенах"""
        session = self.Session()
        new_user = Tokens(user_id=user_id, thread_id=thread_id, prompt_tokens=prompt_tokens, 
                          completion_tokens=completion_tokens, total_tokens=total_tokens,model=model)
        session.add(new_user)
        session.commit()
        session.close()