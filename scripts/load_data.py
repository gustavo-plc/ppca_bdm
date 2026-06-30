import time
import math
from pathlib import Path

import pandas as pd
from cassandra.cluster import Cluster

KEYSPACE = "inmet"
SAMPLE_ROWS = 1000
ROWS_TO_INSERT = 500000

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "processed" / "dados_inmet_clean.csv"


def null_if_nan(value):
    if pd.isna(value):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def prepare_df(df):
    int_cols = ["ano", "mes", "dia", "hora", "umidade"]
    float_cols = [
        "precipitacao",
        "pressao",
        "radiacao",
        "temperatura_bulbo_seco",
        "ponto_de_orvalho",
        "vento_direcao",
        "vento_rajada",
        "vento_velocidade",
    ]

    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    return df


def insert_modelo_a(session, stmt, df):
    for _, row in df.iterrows():
        session.execute(stmt, (
            null_if_nan(row["estado"]),
            null_if_nan(row["data_hora"]),
            null_if_nan(row["ano"]),
            null_if_nan(row["mes"]),
            null_if_nan(row["dia"]),
            null_if_nan(row["hora"]),
            null_if_nan(row["ano_mes"]),
            null_if_nan(row["precipitacao"]),
            null_if_nan(row["pressao"]),
            null_if_nan(row["radiacao"]),
            null_if_nan(row["temperatura_bulbo_seco"]),
            null_if_nan(row["ponto_de_orvalho"]),
            null_if_nan(row["umidade"]),
            null_if_nan(row["vento_direcao"]),
            null_if_nan(row["vento_rajada"]),
            null_if_nan(row["vento_velocidade"]),
        ))


def insert_modelo_b(session, stmt, df):
    for _, row in df.iterrows():
        session.execute(stmt, (
            null_if_nan(row["estado"]),
            null_if_nan(row["ano_mes"]),
            null_if_nan(row["data_hora"]),
            null_if_nan(row["ano"]),
            null_if_nan(row["mes"]),
            null_if_nan(row["dia"]),
            null_if_nan(row["hora"]),
            null_if_nan(row["precipitacao"]),
            null_if_nan(row["pressao"]),
            null_if_nan(row["radiacao"]),
            null_if_nan(row["temperatura_bulbo_seco"]),
            null_if_nan(row["ponto_de_orvalho"]),
            null_if_nan(row["umidade"]),
            null_if_nan(row["vento_direcao"]),
            null_if_nan(row["vento_rajada"]),
            null_if_nan(row["vento_velocidade"]),
        ))


def benchmark_insert(label, fn, session, stmt, df):
    print(f"\nInserindo {len(df)} linhas em {label}...")
    start = time.time()
    fn(session, stmt, df)
    elapsed = time.time() - start
    throughput = len(df) / elapsed
    print(f"  Tempo   : {elapsed:.2f} s")
    print(f"  Linhas/s: {throughput:.1f}")
    return elapsed, throughput


print("=== LOAD DATA — INSERÇÃO DE DADOS ===\n")
print(f"Lendo {ROWS_TO_INSERT} linhas do CSV...")

if not CSV_PATH.exists():
    raise FileNotFoundError(f"CSV não encontrado em: {CSV_PATH}")

df = pd.read_csv(CSV_PATH, nrows=ROWS_TO_INSERT)
df = prepare_df(df)

print(f"Linhas carregadas: {len(df)}")

print("\nConectando ao Cassandra...")
cluster = Cluster(["127.0.0.1"])
session = cluster.connect(KEYSPACE)

stmt_a = session.prepare("""
    INSERT INTO clima_modelo_a (
        estado, data_hora, ano, mes, dia, hora, ano_mes,
        precipitacao, pressao, radiacao,
        temperatura_bulbo_seco, ponto_de_orvalho, umidade,
        vento_direcao, vento_rajada, vento_velocidade
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""")

stmt_b = session.prepare("""
    INSERT INTO clima_modelo_b (
        estado, ano_mes, data_hora, ano, mes, dia, hora,
        precipitacao, pressao, radiacao,
        temperatura_bulbo_seco, ponto_de_orvalho, umidade,
        vento_direcao, vento_rajada, vento_velocidade
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""")

t_a, tp_a = benchmark_insert("clima_modelo_a", insert_modelo_a, session, stmt_a, df)
t_b, tp_b = benchmark_insert("clima_modelo_b", insert_modelo_b, session, stmt_b, df)

print("\n=== RESUMO ===")
print(f"\n{'Métrica':<25} {'Modelo A':>12} {'Modelo B':>12}")
print("-" * 52)
print(f"{'Linhas inseridas':<25} {len(df):>12} {len(df):>12}")
print(f"{'Tempo (s)':<25} {t_a:>12.2f} {t_b:>12.2f}")
print(f"{'Linhas/s':<25} {tp_a:>12.1f} {tp_b:>12.1f}")

cluster.shutdown()
print("\nConexão encerrada.")