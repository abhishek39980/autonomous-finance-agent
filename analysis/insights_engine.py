import pandas as pd
from datetime import datetime, timedelta
from database.db_manager import db
from database.queries import queries
from database.models import Transaction

class InsightsEngine:
    @staticmethod
    def generate_all_insights():
        """
        Analyzes the SQLite transaction table and generates text insights.
        Writes them back to the Insight table.
        """
        print("      [Analysis] Generating insights...")
        
        # Load all transactions from DB
        df = queries.get_all_transactions()
        if df.empty or 'date' not in df.columns:
            return
            
        df['date'] = pd.to_datetime(df['date'])
        
        # We only look at expenses for spending insights
        expenses = df[df['amount'] < 0].copy()
        if expenses.empty:
            return
            
        expenses['amount_abs'] = expenses['amount'].abs()

        insights = []

        # 1. Largest Transaction This Month
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        curr_month_exp = expenses[expenses['date'] >= current_month]
        if not curr_month_exp.empty:
            largest = curr_month_exp.loc[curr_month_exp['amount_abs'].idxmax()]
            month_name = current_month.strftime("%B")
            insights.append(
                f"Your largest transaction this month ({month_name}) was ₹{largest['amount_abs']:,.0f} at {largest['merchant']}."
            )

        # 2. Spending Growth (Current vs Last Month)
        last_month = current_month - timedelta(days=1)
        last_month_start = last_month.replace(day=1)
        
        last_month_exp = expenses[(expenses['date'] >= last_month_start) & (expenses['date'] < current_month)]
        
        curr_total = curr_month_exp['amount_abs'].sum()
        last_total = last_month_exp['amount_abs'].sum()
        
        if last_total > 0:
            growth_pct = ((curr_total - last_total) / last_total) * 100
            if growth_pct > 15:
                insights.append(f"Your spending has increased by {growth_pct:.1f}% compared to last month.")
            elif growth_pct < -15:
                insights.append(f"Great job! Your spending is down {abs(growth_pct):.1f}% compared to last month.")

        # 3. Merchant Concentration
        merchant_totals = expenses.groupby('merchant')['amount_abs'].sum().sort_values(ascending=False)
        total_spending = expenses['amount_abs'].sum()
        if not merchant_totals.empty and total_spending > 0:
            top_merchant = merchant_totals.index[0]
            top_amt = merchant_totals.iloc[0]
            concentration = (top_amt / total_spending) * 100
            if concentration > 20 and top_merchant.lower() != "unknown" and top_merchant.lower() != "other":
                insights.append(f"{top_merchant} accounts for {concentration:.1f}% of your total expenses.")

        # 4. Category Spikes
        if not curr_month_exp.empty and not last_month_exp.empty:
            curr_cats = curr_month_exp.groupby('category')['amount_abs'].sum()
            last_cats = last_month_exp.groupby('category')['amount_abs'].sum()
            
            for cat in curr_cats.index:
                if cat in last_cats:
                    curr_cat_amt = curr_cats[cat]
                    last_cat_amt = last_cats[cat]
                    if last_cat_amt > 0:
                         spike = ((curr_cat_amt - last_cat_amt) / last_cat_amt) * 100
                         if spike > 50 and curr_cat_amt > 1000: # significant spike
                             insights.append(f"{cat} spending spiked {spike:.0f}% compared to last month.")

        # Save generated insights to db (keep only latest ones or append)
        for text in list(set(insights)):  # unique
             queries.add_insight(text)

insights_engine = InsightsEngine()
