import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from database.queries import queries

class ForecastingEngine:
    @staticmethod
    def forecast_next_month():
        """
        Uses simple Linear Regression on monthly aggregate spending to forecast next month's total spending.
        """
        print("      [Analysis] Forecasting future spending...")
        df = queries.get_all_transactions()
        if df.empty or 'date' not in df.columns:
            return {"forecast_total": 0, "categories": {}}

        df['date'] = pd.to_datetime(df['date'])
        expenses = df[df['amount'] < 0].copy()
        if expenses.empty:
            return {"forecast_total": 0, "categories": {}}
            
        expenses['amount_abs'] = expenses['amount'].abs()
        
        # Group by Year-Month
        expenses['year_month'] = expenses['date'].dt.to_period('M')
        monthly_totals = expenses.groupby('year_month')['amount_abs'].sum().reset_index()
        
        if len(monthly_totals) < 3:
            # Not enough data for regression, return naive average
            avg = float(monthly_totals['amount_abs'].mean())
            return {"forecast_total": avg, "categories": {}}

        # Prepare data for Scikit-Learn (predict Y from time X)
        # X: sequence of months (0, 1, 2, 3...)
        X = np.arange(len(monthly_totals)).reshape(-1, 1)
        y = monthly_totals['amount_abs'].values

        model = LinearRegression()
        model.fit(X, y)
        
        # Predict next month (X = len)
        next_month_idx = np.array([[len(monthly_totals)]])
        prediction = model.predict(next_month_idx)[0]
        
        # Bound it to 0 just in case
        prediction = max(0.0, float(prediction))
        
        # Category breakdown forecast (naive proportion approach to complement regression)
        cat_history = expenses.groupby('category')['amount_abs'].sum()
        total_history = cat_history.sum()
        
        cat_forecast = {}
        if total_history > 0:
            for cat, amt in cat_history.items():
                proportion = amt / total_history
                cat_forecast[cat] = proportion * prediction

        return {
            "forecast_total": prediction,
            "categories": cat_forecast
        }

forecasting_engine = ForecastingEngine()
