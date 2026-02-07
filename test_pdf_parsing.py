import sys
import os
import pandas as pd

# Add current directory to path so we can import tools
sys.path.append(os.getcwd())

try:
    from tools.pdf_tools import read_pdf_statement
except ImportError:
    # If running from root, try appending proper path
    sys.path.append(os.path.join(os.getcwd(), 'autonomous-agent'))
    from tools.pdf_tools import read_pdf_statement

def test_parsing():
    pdf_path = "statement.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return

    print(f"Testing parsing of {pdf_path} with Text-Stream Strategy...")
    df = read_pdf_statement(pdf_path)
    
    if isinstance(df, str):
        print(f"Parsing failed with message: {df}")
    elif df is None:
        print("Parsing returned None.")
    else:
        print("\nSuccess! DataFrame shape:", df.shape)
        print("\nColumns:", df.columns.tolist())
        print("\nFirst 10 rows:")
        print(df.head(10))
        
        # Check for specific requirements
        if 'Description' in df.columns:
            print("\nSample Descriptions (First 3):")
            print(df['Description'].head(3).tolist())
            
        print("\nAmount Check:")
        if 'Amount' in df.columns:
            neg_count = (df['Amount'] < 0).sum()
            pos_count = (df['Amount'] > 0).sum()
            print(f"Negative Amounts (Spend): {neg_count}")
            print(f"Positive Amounts (Income): {pos_count}")
            print("\nFirst 5 Amounts:")
            print(df[['Description', 'Amount']].head(5))

if __name__ == "__main__":
    test_parsing()
