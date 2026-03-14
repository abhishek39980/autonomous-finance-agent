from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    merchant = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)
    account = Column(String(100), nullable=True)
    source_file = Column(String(255), nullable=True)
    raw_description = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "merchant": self.merchant,
            "amount": self.amount,
            "category": self.category,
            "account": self.account,
            "source_file": self.source_file,
            "raw_description": self.raw_description
        }

class RecurringPayment(Base):
    __tablename__ = 'recurring_payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant = Column(String(255), nullable=False, unique=True)
    average_amount = Column(Float, nullable=False)
    interval_days = Column(Float, nullable=False)
    last_seen = Column(DateTime, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "merchant": self.merchant,
            "average_amount": self.average_amount,
            "interval_days": self.interval_days,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }

class Insight(Base):
    __tablename__ = 'insights'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    text = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "text": self.text
        }
