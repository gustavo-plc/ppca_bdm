import pandas as pd
import os

INPUT_PATH = "data/raw/dados_inmet.csv"   # ajuste o nome
OUTPUT_PATH = "data/processed/dados_inmet_clean.csv"

df = pd.read_csv(
    INPUT_PATH,
    encoding="latin-1",
    sep=",",
    dtype=str,
    low_memory=False
)



df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(".", "_", regex=False)
    .str.replace(" ", "_", regex=False)
    .str.replace("ç", "c", regex=False)
    .str.replace("ã", "a", regex=False)
    .str.replace("á", "a", regex=False)
    .str.replace("à", "a", regex=False)
    .str.replace("é", "e", regex=False)
    .str.replace("ê", "e", regex=False)
    .str.replace("í", "i", regex=False)
    .str.replace("ó", "o", regex=False)
    .str.replace("ô", "o", regex=False)
    .str.replace("ú", "u", regex=False)
)

df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
df["dia"] = pd.to_numeric(df["dia"], errors="coerce")
df["hora"] = pd.to_numeric(df["hora"], errors="coerce")

df["ano_mes"] = (
    df["ano"].astype("Int64").astype(str) + "-" +
    df["mes"].astype("Int64").astype(str).str.zfill(2)
)

df["data_hora"] = pd.to_datetime(
    df["ano"].astype("Int64").astype(str) + "-" +
    df["mes"].astype("Int64").astype(str).str.zfill(2) + "-" +
    df["dia"].astype("Int64").astype(str).str.zfill(2) + " " +
    df["hora"].astype("Int64").astype(str).str.zfill(2) + ":00:00",
    format="%Y-%m-%d %H:%M:%S",
    errors="coerce"
)

os.makedirs("data/processed", exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

print(f"Concluído! {len(df)} linhas salvas em {OUTPUT_PATH}")
print(df[["estado", "ano", "mes", "dia", "hora", "ano_mes", "data_hora"]].head(10))