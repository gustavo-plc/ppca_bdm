from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "processed" / "dados_inmet_clean.csv"

print("=== EXPLORAÇÃO DO DATASET ===")
print(f"Diretório do script : {Path(__file__).resolve().parent}")
print(f"Raiz do projeto     : {BASE_DIR}")
print(f"Caminho do CSV      : {CSV_PATH}")

if not CSV_PATH.exists():
    raise FileNotFoundError(f"CSV não encontrado em: {CSV_PATH}")

df = pd.read_csv(CSV_PATH)

print("\n=== COLUNAS DISPONÍVEIS ===")
print(df.columns.tolist())

print("\n=== TAMANHO DO DATASET ===")
print(f"Linhas: {len(df)}")

print("\n=== AMOSTRA ===")
print(df.head(5).to_string())

COL_ESTADO = "estado"

possible_date_cols = [
    "ano_mes",
    "data",
    "data_medicao",
    "data_hora",
    "datetime",
    "dt_medicao"
]

date_col = None
for col in possible_date_cols:
    if col in df.columns:
        date_col = col
        break

if date_col is None:
    raise ValueError(
        "Não encontrei uma coluna de data/ano_mes esperada. "
        "Verifique os nomes das colunas impressos acima."
    )

print("\n=== COLUNA USADA PARA DATA ===")
print(date_col)

if date_col == "ano_mes":
    df["ano_mes_explorado"] = df["ano_mes"].astype(str)
else:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if df[date_col].isna().all():
        raise ValueError(
            f"Não foi possível converter a coluna '{date_col}' para datetime."
        )
    df["ano_mes_explorado"] = df[date_col].dt.strftime("%Y-%m")
    df["ano_explorado"] = df[date_col].dt.year

print("\n=== ESTADOS DISPONÍVEIS ===")
print(sorted(df[COL_ESTADO].dropna().astype(str).unique().tolist()))

print("\n=== ANO_MES DISPONÍVEIS (GERAL) ===")
ano_mes_unicos = sorted(df["ano_mes_explorado"].dropna().unique().tolist())
print(ano_mes_unicos)

print("\n=== TOTAL DE ANO_MES DISTINTOS ===")
print(len(ano_mes_unicos))

print("\n=== ANO_MES DO DF ===")
df_df = df[df[COL_ESTADO].astype(str) == "DF"].copy()
ano_mes_df = sorted(df_df["ano_mes_explorado"].dropna().unique().tolist())
print(ano_mes_df)

print("\n=== ANO_MES DO DF EM 2005 ===")
ano_mes_df_2005 = [x for x in ano_mes_df if x.startswith("2005-")]
print(ano_mes_df_2005)

print("\n=== CONTAGEM DE LINHAS DO DF EM 2005 ===")
if date_col == "ano_mes":
    qtd_df_2005 = df_df[df_df["ano_mes_explorado"].str.startswith("2005-")].shape[0]
else:
    qtd_df_2005 = df_df[df_df["ano_explorado"] == 2005].shape[0]
print(qtd_df_2005)

print("\n=== CONTAGEM POR ANO_MES NO DF EM 2005 ===")
contagem = (
    df_df[df_df["ano_mes_explorado"].str.startswith("2005-")]
    .groupby("ano_mes_explorado")
    .size()
    .reset_index(name="qtd_linhas")
    .sort_values("ano_mes_explorado")
)
print(contagem.to_string(index=False))

print("\n=== FIM ===")