import pandas as pd
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .db_manager import db
from .models import Transaction, RecurringPayment, Insight

class QueryManager:
    @staticmethod
    def ingest_transactions(df: pd.DataFrame, source_file: str) -> int:
        """
        Takes a Pandas DataFrame of transactions and inserts them into SQLite.
        Expects columns: Date, Amount (or Withdrawal/Deposit), Description, Category.
        """
        if df is None or df.empty:
            return 0

        session = db.get_session()
        count = 0
        try:
            for _, row in df.iterrows():
                # Parse Date
                date_val = None
                date_candidates = ["Date", "ValueDate", "Transaction Date"]
                for dc in date_candidates:
                    if dc in df.columns and pd.notna(row[dc]):
                        date_val = pd.to_datetime(row[dc])
                        break
                
                if date_val is None:
                    continue  # Skip rows without a date
                
                # Parse Amount
                amount_val = 0.0
                if "Amount" in df.columns and pd.notna(row["Amount"]):
                    val = row["Amount"]
                    if isinstance(val, str):
                        try:
                            val = float(val.replace(',', '').replace('₹', '').replace('$', '').strip())
                        except ValueError:
                            pass
                    amount_val = float(val) if isinstance(val, (int, float)) else 0.0
                elif "Withdrawal" in df.columns and pd.notna(row["Withdrawal"]) and str(row["Withdrawal"]).strip() != "":
                    try:
                        amount_val = -abs(float(str(row["Withdrawal"]).replace(',', '')))
                    except ValueError:
                        pass
                elif "Deposit" in df.columns and pd.notna(row["Deposit"]) and str(row["Deposit"]).strip() != "":
                    try:
                        amount_val = abs(float(str(row["Deposit"]).replace(',', '')))
                    except ValueError:
                        pass

                # Parse Description and Merchant
                desc_col = None
                for c in ["Description", "Narration", "Particulars"]:
                    if c in df.columns:
                        desc_col = c
                        break
                
                raw_desc = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else ""
                
                # For basic schema ingestion, we treat the cleaned Category/Merchant.
                # If finance_tools.py already cleaned it into a "Merchant" column, use it, else fallback to raw.
                merchant_val = row.get("Merchant", raw_desc)
                if pd.isna(merchant_val):
                    merchant_val = raw_desc
                    
                category_val = row.get("Category", "Other")
                if pd.isna(category_val):
                     category_val = "Other"

                # Insert Transaction
                txn = Transaction(
                    date=date_val,
                    merchant=str(merchant_val),
                    amount=amount_val,
                    category=str(category_val),
                    source_file=source_file,
                    raw_description=raw_desc
                )
                session.add(txn)
                count += 1
            
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            print(f"Error during database ingestion: {e}")
            return 0
        finally:
            session.close()

    @staticmethod
    def get_all_transactions() -> pd.DataFrame:
        """Returns all transactions as a Pandas DataFrame."""
        try:
             # Fast aggregation by loading directly via pandas from engine
             query = "SELECT * FROM transactions ORDER BY date DESC"
             df = pd.read_sql(query, con=db.engine)
             return df
        except Exception as e:
             print(f"Error reading transactions: {e}")
             return pd.DataFrame()

    @staticmethod
    def get_spending_by_category(months_back: int = 1) -> Dict[str, float]:
        """Aggregate spending by category for the last N months."""
        session = db.get_session()
        try:
            cutoff = datetime.now() - timedelta(days=months_back * 30)
            results = session.query(
                Transaction.category,
                func.sum(Transaction.amount).label('total')
            ).filter(
                Transaction.date >= cutoff,
                Transaction.amount < 0
            ).group_by(
                Transaction.category
            ).all()
            return {r[0]: abs(r[1]) for r in results}
        finally:
            session.close()

    @staticmethod
    def get_recent_insights() -> List[Dict[str, Any]]:
        """Fetch the latest insights generated by the engine."""
        session = db.get_session()
        try:
            results = session.query(Insight).order_by(Insight.created_at.desc()).limit(10).all()
            return [r.to_dict() for r in results]
        finally:
            session.close()

    @staticmethod
    def add_insight(text: str):
        session = db.get_session()
        try:
            insight = Insight(text=text)
            session.add(insight)
            session.commit()
        except:
             session.rollback()
        finally:
             session.close()
             
    @staticmethod
    def get_recurring_payments() -> List[Dict[str, Any]]:
        session = db.get_session()
        try:
            results = session.query(RecurringPayment).all()
            return [r.to_dict() for r in results]
        finally:
            session.close()
            
    @staticmethod
    def save_recurring_payments(payments: List[Dict]):
        session = db.get_session()
        try:
            # Clear old recurring payments table (sync state)
            session.query(RecurringPayment).delete()
            for p in payments:
                 rp = RecurringPayment(
                     merchant=p['merchant'],
                     average_amount=p['average_amount'],
                     interval_days=p['interval_days'],
                     last_seen=p['last_seen']
                 )
                 session.add(rp)
            session.commit()
        except Exception as e:
             session.rollback()
             print(f"Error saving recurring payments: {e}")
        finally:
             session.close()

queries = QueryManager()
