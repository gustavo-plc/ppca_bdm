import pandas as pd

CSV_PATH = "data/processed/dados_inmet_clean.csv"

df = pd.read_csv(CSV_PATH, nrows=5)
print("Colunas do CSV clean:")
for col in df.columns:
    print(f"- {col}")