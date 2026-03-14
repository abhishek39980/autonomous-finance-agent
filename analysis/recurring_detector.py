import pandas as pd
import numpy as np
from database.queries import queries

class RecurringDetector:
    @staticmethod
    def detect_recurring_payments():
        """
        Analyzes transaction history to find recurring subscriptions with:
        - Amount variance <= 10%
        - Interval variance <= 5 days
        """
        print("      [Analysis] Detecting recurring payments...")
        
        df = queries.get_all_transactions()
        if df.empty or 'date' not in df.columns:
            return []

        df['date'] = pd.to_datetime(df['date'])
        
        # Filter for expenses only, ignoring common non-recurring ones
        expenses = df[df['amount'] < 0].copy()
        expenses['amount_abs'] = expenses['amount'].abs()
        expenses = expenses[~expenses['category'].isin(["Transfer", "Cash Withdrawal", "Other"])]

        # Group by merchant
        recurring_list = []
        for merchant, group in expenses.groupby('merchant'):
            if len(group) < 3 or merchant.lower() in ['unknown', 'other', 'upi', 'atm']:
                continue
                
            group = group.sort_values('date')
            
            # 1. Amount variance check
            amounts = group['amount_abs'].values
            mean_amt = np.mean(amounts)
            std_amt = np.std(amounts)
            
            # Skip if variance is > 10% of mean
            if (std_amt / mean_amt) > 0.10:
                continue
                
            # 2. Interval check
            dates = group['date'].values
            if len(dates) < 2:
                continue
                
            # Calculate days between consecutive transactions
            intervals = np.diff(dates).astype('timedelta64[D]').astype(int)
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            
            # Verify it's a regular interval (roughly weekly, monthly, quarterly, yearly with grace)
            is_regular = False
            for expected in [7, 30, 90, 365]:
                # within 5 days of a typical interval footprint?
                if abs(mean_interval - expected) <= 5 and std_interval <= 5:
                    is_regular = True
                    break
            
            if is_regular:
                recurring_list.append({
                    "merchant": merchant,
                    "average_amount": float(mean_amt),
                    "interval_days": float(mean_interval),
                    "last_seen": pd.to_datetime(dates[-1])
                })

        # Save to DB
        if recurring_list:
            queries.save_recurring_payments(recurring_list)
            
        return recurring_list

recurring_detector = RecurringDetector()
