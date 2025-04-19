from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

Base = declarative_base()

class Worker(Base):
    __tablename__ = 'workers'

    id = Column(Integer, primary_key=True, autoincrement=True)  # <-- هنا التعديل
    name = Column(String, nullable=False)

    logs = relationship("Log", back_populates="worker")

class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, autoincrement=True)  # <-- وهنا
    worker_id = Column(Integer, ForeignKey('workers.id'), nullable=False)
    in_date = Column(Integer, nullable=False)
    out_date = Column(Integer, nullable=False)

    worker = relationship("Worker", back_populates="logs")

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
engine = create_engine(f'sqlite:///{db_path}', echo=False)

# إنشاء الجداول
Base.metadata.create_all(engine)

# إعداد جلسة الاتصال
Session = sessionmaker(bind=engine)
session = Session()


