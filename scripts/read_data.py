import time
import csv
import os
import pandas as pd
from datetime import datetime
from cassandra.cluster import Cluster

KEYSPACE  = "inmet"
ESTADOS   = ["GO", "DF", "MT", "MS"]
CSV_OUT   = "results/read_benchmark_results.csv"
N_RUNS    = 5   # 1ª execução descartada; média das 4 seguintes

# Verões disponíveis nas 230k linhas inseridas (ajuste se necessário após verificar os dados)
# Verão rotulado pelo ano de FIM: verão AAAA = 21/dez/(AAAA-1) a 20/mar/AAAA
VERAOS_ALVO = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]


def meses_do_verao(ano_fim):
    """Retorna os 4 ano_mes que cobrem o verão rotulado pelo ano de fim."""
    return [
        f"{ano_fim - 1}-12",
        f"{ano_fim}-01",
        f"{ano_fim}-02",
        f"{ano_fim}-03",
    ]


def periodo_do_verao(ano_fim):
    """Retorna timestamps de início e fim do verão."""
    inicio = pd.Timestamp(f"{ano_fim - 1}-12-21 00:00:00")
    fim    = pd.Timestamp(f"{ano_fim}-03-20 23:00:00")
    return inicio, fim


def buscar_modelo_a(session, stmt, estados, veraos):
    """Busca dados no Modelo A para todos os estados e verões."""
    rows_total = []
    for verao in veraos:
        inicio, fim = periodo_do_verao(verao)
        ano_inicio  = verao - 1  # dezembro do ano anterior
        ano_fim_v   = verao      # janeiro a março do ano de fim
        for estado in estados:
            for ano in [ano_inicio, ano_fim_v]:
                result = list(session.execute(stmt, (
                    ano,
                    estado,
                    inicio,
                    fim,
                )))
                rows_total.extend(result)
    return rows_total


def buscar_modelo_b(session, stmt, estados, veraos):
    """Busca dados no Modelo B para todos os estados e verões."""
    rows_total = []
    for verao in veraos:
        inicio, fim = periodo_do_verao(verao)
        meses = meses_do_verao(verao)
        for estado in estados:
            for mes in meses:
                result = list(session.execute(stmt, (
                    estado,
                    mes,
                    inicio,
                    fim,
                )))
                rows_total.extend(result)
    return rows_total


def processar_resultado(rows, estados, veraos):
    """
    Calcula a média de precipitação por estado e por verão,
    e identifica o estado vencedor por verão e no geral.
    """
    # Acumula precipitação por (estado, verao)
    acum = {}
    for estado in estados:
        for verao in veraos:
            acum[(estado, verao)] = {"soma": 0.0, "count": 0}

    for row in rows:
        try:
            est   = row.estado
            ts    = row.data_hora
            precip = row.precipitacao
        except AttributeError:
            continue

        if est not in estados or precip is None:
            continue

        # Mapeia timestamp para o verão correto
        mes = ts.month
        ano = ts.year
        if mes == 12:
            verao_label = ano + 1
        else:
            verao_label = ano

        if (est, verao_label) in acum:
            acum[(est, verao_label)]["soma"]  += precip
            acum[(est, verao_label)]["count"] += 1

    # Médias por estado e verão
    medias = {}
    for (est, verao), vals in acum.items():
        if vals["count"] > 0:
            medias[(est, verao)] = vals["soma"] / vals["count"]
        else:
            medias[(est, verao)] = None

    # Vencedor por verão
    vencedores_por_verao = {}
    for verao in veraos:
        melhor_estado = None
        melhor_media  = -1
        for estado in estados:
            media = medias.get((estado, verao))
            if media is not None and media > melhor_media:
                melhor_media  = media
                melhor_estado = estado
        vencedores_por_verao[verao] = (melhor_estado, melhor_media)

    # Vencedor geral (somando todos os verões)
    total_geral = {}
    for estado in estados:
        valores = [medias[(estado, v)] for v in veraos if medias.get((estado, v)) is not None]
        total_geral[estado] = sum(valores) / len(valores) if valores else None

    vencedor_geral = max(
        [(est, val) for est, val in total_geral.items() if val is not None],
        key=lambda x: x[1]
    )

    return medias, vencedores_por_verao, vencedor_geral, total_geral


def executar_benchmark(session, modelo, buscar_fn, stmt, estados, veraos):
    """
    Executa N_RUNS rodadas de leitura e processamento.
    Descarta a 1ª execução e retorna a média das demais.
    """
    tempos_leitura     = []
    tempos_processamento = []
    tempos_total       = []
    linhas_lidas       = []

    print(f"\n{'='*55}")
    print(f"  BENCHMARK DE LEITURA — {modelo}")
    print(f"{'='*55}")

    resultado_final = None

    for i in range(1, N_RUNS + 1):
        label = f"  Execução {i}/5" + (" [DESCARTADA]" if i == 1 else "")
        print(label)

        # --- leitura ---
        t0 = time.time()
        rows = buscar_fn(session, stmt, estados, veraos)
        t1 = time.time()

        # --- processamento ---
        medias, venc_por_verao, venc_geral, total_geral = processar_resultado(rows, estados, veraos)
        t2 = time.time()

        t_leit  = t1 - t0
        t_proc  = t2 - t1
        t_total = t2 - t0
        n_rows  = len(rows)

        print(f"    Linhas lidas     : {n_rows}")
        print(f"    Tempo leitura    : {t_leit:.4f} s")
        print(f"    Tempo processam. : {t_proc:.4f} s")
        print(f"    Tempo total      : {t_total:.4f} s")

        if i == 1:
            resultado_final = (medias, venc_por_verao, venc_geral, total_geral)
            continue  # descarta a 1ª execução das métricas

        tempos_leitura.append(t_leit)
        tempos_processamento.append(t_proc)
        tempos_total.append(t_total)
        linhas_lidas.append(n_rows)
        resultado_final = (medias, venc_por_verao, venc_geral, total_geral)

    media_t_leit  = sum(tempos_leitura) / len(tempos_leitura)
    media_t_proc  = sum(tempos_processamento) / len(tempos_processamento)
    media_t_total = sum(tempos_total) / len(tempos_total)
    media_linhas  = sum(linhas_lidas) / len(linhas_lidas)

    print(f"\n  --- Médias das execuções 2 a 5 ---")
    print(f"  Linhas lidas     : {media_linhas:.1f}")
    print(f"  Tempo leitura    : {media_t_leit:.4f} s")
    print(f"  Tempo processam. : {media_t_proc:.4f} s")
    print(f"  Tempo total      : {media_t_total:.4f} s")

    return {
        "modelo":           modelo,
        "media_t_leitura":  media_t_leit,
        "media_t_proc":     media_t_proc,
        "media_t_total":    media_t_total,
        "media_linhas":     media_linhas,
    }, resultado_final


def imprimir_resultado_analitico(modelo, medias, venc_por_verao, venc_geral, total_geral, estados, veraos):
    print(f"\n{'='*55}")
    print(f"  RESULTADO ANALÍTICO — {modelo}")
    print(f"{'='*55}")

    print("\n  Média de precipitação por estado e verão (mm):")
    header = f"  {'Verão':<10}" + "".join(f"{est:>10}" for est in estados)
    print(header)
    print("  " + "-" * (10 + 10 * len(estados)))
    for verao in veraos:
        linha = f"  {verao:<10}"
        for estado in estados:
            val = medias.get((estado, verao))
            linha += f"{val:>10.4f}" if val is not None else f"{'N/A':>10}"
        print(linha)

    print("\n  Vencedor por verão (estado com maior chuva média):")
    for verao in veraos:
        estado, media = venc_por_verao[verao]
        if estado:
            print(f"    Verão {verao}: {estado} ({media:.4f} mm)")
        else:
            print(f"    Verão {verao}: sem dados")

    print("\n  Médias gerais (todos os verões agregados):")
    for estado in estados:
        val = total_geral.get(estado)
        print(f"    {estado}: {val:.4f} mm" if val else f"    {estado}: N/A")

    venc_nome, venc_media = venc_geral
    print(f"\n  *** Estado vencedor geral: {venc_nome} com média de {venc_media:.4f} mm ***")


def salvar_csv(resultados_benchmark, medias, venc_por_verao, venc_geral, total_geral, estados, veraos):
    os.makedirs("results", exist_ok=True)

    # Arquivo 1 — métricas de benchmark
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "modelo", "media_linhas_lidas",
            "media_tempo_leitura_s", "media_tempo_processamento_s", "media_tempo_total_s"
        ])
        for r in resultados_benchmark:
            writer.writerow([
                r["modelo"],
                f"{r['media_linhas']:.1f}",
                f"{r['media_t_leitura']:.4f}",
                f"{r['media_t_proc']:.4f}",
                f"{r['media_t_total']:.4f}",
            ])
    print(f"\n  Benchmark salvo em: {CSV_OUT}")

    # Arquivo 2 — resultado analítico
    csv_analitico = "results/read_resultado_analitico.csv"
    with open(csv_analitico, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["verao", "estado", "media_precipitacao_mm"])
        for verao in veraos:
            for estado in estados:
                val = medias.get((estado, verao))
                writer.writerow([verao, estado, f"{val:.4f}" if val else "N/A"])
        writer.writerow([])
        writer.writerow(["vencedor_geral", venc_geral[0], f"{venc_geral[1]:.4f}"])
    print(f"  Resultado analítico salvo em: {csv_analitico}")


# =============================================================
# EXECUÇÃO PRINCIPAL
# =============================================================

print("=== READ DATA — BENCHMARK DE LEITURA ===\n")
print(f"Estados analisados : {', '.join(ESTADOS)}")
print(f"Verões analisados  : {', '.join(str(v) for v in VERAOS_ALVO)}")
print(f"Execuções por modelo: {N_RUNS} (1ª descartada, média das 4 seguintes)")

print("\nConectando ao Cassandra...")
cluster = Cluster(["127.0.0.1"])
session = cluster.connect(KEYSPACE)

# --- Prepared statements ---
stmt_a = session.prepare("""
    SELECT estado, data_hora, precipitacao
    FROM clima_modelo_a
    WHERE ano = ? AND estado = ?
      AND data_hora >= ? AND data_hora <= ?
""")

stmt_b = session.prepare("""
    SELECT estado, data_hora, precipitacao
    FROM clima_modelo_b
    WHERE estado = ? AND ano_mes = ?
      AND data_hora >= ? AND data_hora <= ?
""")

# --- Benchmark Modelo A ---
bench_a, resultado_a = executar_benchmark(
    session, "Modelo A", buscar_modelo_a, stmt_a, ESTADOS, VERAOS_ALVO
)
medias_a, venc_por_verao_a, venc_geral_a, total_geral_a = resultado_a
imprimir_resultado_analitico("Modelo A", medias_a, venc_por_verao_a, venc_geral_a, total_geral_a, ESTADOS, VERAOS_ALVO)

# --- Benchmark Modelo B ---
bench_b, resultado_b = executar_benchmark(
    session, "Modelo B", buscar_modelo_b, stmt_b, ESTADOS, VERAOS_ALVO
)
medias_b, venc_por_verao_b, venc_geral_b, total_geral_b = resultado_b
imprimir_resultado_analitico("Modelo B", medias_b, venc_por_verao_b, venc_geral_b, total_geral_b, ESTADOS, VERAOS_ALVO)

# --- Comparativo final ---
print("\n" + "="*55)
print("  COMPARATIVO DE BENCHMARK — LEITURA")
print("="*55)
print(f"\n  {'Métrica':<35} {'Modelo A':>12} {'Modelo B':>12}")
print("  " + "-" * 60)
print(f"  {'Linhas lidas (média)':<35} {bench_a['media_linhas']:>12.1f} {bench_b['media_linhas']:>12.1f}")
print(f"  {'Tempo leitura Cassandra (s)':<35} {bench_a['media_t_leitura']:>12.4f} {bench_b['media_t_leitura']:>12.4f}")
print(f"  {'Tempo processamento Python (s)':<35} {bench_a['media_t_proc']:>12.4f} {bench_b['media_t_proc']:>12.4f}")
print(f"  {'Tempo total (s)':<35} {bench_a['media_t_total']:>12.4f} {bench_b['media_t_total']:>12.4f}")
print(f"\n  Estado vencedor geral (Modelo A): {venc_geral_a[0]} ({venc_geral_a[1]:.4f} mm)")
print(f"  Estado vencedor geral (Modelo B): {venc_geral_b[0]} ({venc_geral_b[1]:.4f} mm)")

# --- Salvar CSVs ---
salvar_csv(
    [bench_a, bench_b],
    medias_a,  # usa resultado do Modelo A como fonte analítica (os dois devem ser iguais)
    venc_por_verao_a,
    venc_geral_a,
    total_geral_a,
    ESTADOS,
    VERAOS_ALVO,
)

cluster.shutdown()
print("\nConexão encerrada.")