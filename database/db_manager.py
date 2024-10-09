from sqlalchemy import create_engine, Column, String, Integer, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, exists
import sqlalchemy
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Подгружаем базу данных
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
port = os.getenv('DB_PORT')
database = os.getenv('DB_DATABASE')

DATABASE_URL = f'postgresql://{username}:{password}@{host}:{port}/{database}'

# Создание базы данных и настройка SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = sqlalchemy.orm.declarative_base()

# Определение модели для таблицы user_records
class User(Base):
    __tablename__ = 'user_records'
    
    user_id = Column(String, primary_key=True)
    thread_id = Column(String)

# Определение модели для таблицы tokens
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
        try:
            Base.metadata.create_all(self.engine)
            logging.info("Таблицы успешно созданы.")
        except Exception as e:
            logging.error(f"Ошибка при создании таблиц: {e}")

    def add_user(self, user_id, thread_id):
        """Добавляем пользователя"""
        session = self.Session()
        try:
            new_user = User(user_id=user_id, thread_id=thread_id)
            session.add(new_user)
            session.commit()
            logging.info(f"Пользователь {user_id} успешно добавлен.")
        except Exception as e:
            logging.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
            session.rollback()
        finally:
            session.close()

    def update_user(self, user_id, thread_id):
        """Замена старого thread_id на новый"""
        session = self.Session()
        try:
            session.query(User).filter(User.user_id == user_id).update({
                User.thread_id: thread_id
            })
            session.commit()
            logging.info(f"Пользователь {user_id} обновил thread_id на {thread_id}.")
        except Exception as e:
            logging.error(f"Ошибка при обновлении пользователя {user_id}: {e}")
            session.rollback()
        finally:
            session.close()

    def exists(self, user_id):
        """Проверка существования пользователя по user_id"""
        session = self.Session()
        try:
            exists_query = session.query(exists().where(User.user_id == user_id)).scalar()
            return exists_query
        except Exception as e:
            logging.error(f"Ошибка при проверке существования пользователя {user_id}: {e}")
            return False
        finally:
            session.close()
    
    def add_tokens(self, user_id, thread_id, prompt_tokens, completion_tokens, total_tokens, model):
        """Добавляем информацию о токенах"""
        session = self.Session()
        try:
            new_token = Tokens(user_id=user_id, thread_id=thread_id, prompt_tokens=prompt_tokens, 
                               completion_tokens=completion_tokens, total_tokens=total_tokens, model=model)
            session.add(new_token)
            session.commit()
            logging.info(f"Токены успешно добавлены для пользователя {user_id}.")
        except Exception as e:
            logging.error(f"Ошибка при добавлении токенов для пользователя {user_id}: {e}")
            session.rollback()
        finally:
            session.close()
