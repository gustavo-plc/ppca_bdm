import time
import csv
import os
import pandas as pd
from cassandra.cluster import Cluster

KEYSPACE  = "inmet"
ESTADOS   = ["GO", "DF", "MT", "MS"]
ANOS      = list(range(2000, 2021))
MESES     = [f"{m:02d}" for m in range(1, 13)]
CSV_OUT   = "results/read_benchmark_results.csv"
N_RUNS    = 5


def buscar_modelo_a(session, stmt, estados, anos):
    rows_total = []
    for ano in anos:
        for estado in estados:
            result = list(session.execute(stmt, (ano, estado)))
            rows_total.extend(result)
    return rows_total


def buscar_modelo_b(session, stmt, estados, anos):
    rows_total = []
    for ano in anos:
        for estado in estados:
            for mes in MESES:
                ano_mes = f"{ano}-{mes}"
                result = list(session.execute(stmt, (estado, ano_mes)))
                # injeta o ano no resultado para processamento
                for row in result:
                    rows_total.append((row.estado, ano, row.precipitacao))
    return rows_total


def processar_resultado_a(rows, estados, anos):
    acum = {(estado, ano): {"soma": 0.0, "count": 0}
            for estado in estados for ano in anos}
    for row in rows:
        try:
            est    = row.estado
            ano    = int(row.ano)
            precip = row.precipitacao
        except AttributeError:
            continue
        if est not in estados or precip is None or ano is None:
            continue
        if (est, ano) in acum:
            acum[(est, ano)]["soma"]  += precip
            acum[(est, ano)]["count"] += 1
    return calcular_medias_e_vencedores(acum, estados, anos)


def processar_resultado_b(rows, estados, anos):
    acum = {(estado, ano): {"soma": 0.0, "count": 0}
            for estado in estados for ano in anos}
    for est, ano, precip in rows:
        if est not in estados or precip is None:
            continue
        if (est, ano) in acum:
            acum[(est, ano)]["soma"]  += precip
            acum[(est, ano)]["count"] += 1
    return calcular_medias_e_vencedores(acum, estados, anos)


def calcular_medias_e_vencedores(acum, estados, anos):
    medias = {}
    for (est, ano), vals in acum.items():
        medias[(est, ano)] = vals["soma"] / vals["count"] if vals["count"] > 0 else None

    vencedores_por_ano = {}
    for ano in anos:
        melhor_estado, melhor_media = None, -1
        for estado in estados:
            val = medias.get((estado, ano))
            if val is not None and val > melhor_media:
                melhor_media, melhor_estado = val, estado
        vencedores_por_ano[ano] = (melhor_estado, melhor_media)

    total_geral = {}
    for estado in estados:
        vals = [medias[(estado, a)] for a in anos if medias.get((estado, a)) is not None]
        total_geral[estado] = sum(vals) / len(vals) if vals else None

    candidatos = [(est, val) for est, val in total_geral.items() if val is not None]
    venc_geral = max(candidatos, key=lambda x: x[1]) if candidatos else (None, None)

    return medias, vencedores_por_ano, venc_geral, total_geral


def executar_benchmark(session, modelo, buscar_fn, processar_fn, stmt, estados, anos):
    tempos_leitura, tempos_proc, tempos_total, linhas_lidas = [], [], [], []
    resultado_final = None

    print(f"\n{'='*55}")
    print(f"  BENCHMARK DE LEITURA — {modelo}")
    print(f"{'='*55}")

    for i in range(1, N_RUNS + 1):
        label = f"  Execução {i}/5" + (" [DESCARTADA]" if i == 1 else "")
        print(label)

        t0   = time.time()
        rows = buscar_fn(session, stmt, estados, anos)
        t1   = time.time()
        medias, venc_por_ano, venc_geral, total_geral = processar_fn(rows, estados, anos)
        t2   = time.time()

        t_leit, t_proc, t_total = t1-t0, t2-t1, t2-t0
        n_rows = len(rows)

        print(f"    Linhas lidas     : {n_rows}")
        print(f"    Tempo leitura    : {t_leit:.4f} s")
        print(f"    Tempo processam. : {t_proc:.4f} s")
        print(f"    Tempo total      : {t_total:.4f} s")

        resultado_final = (medias, venc_por_ano, venc_geral, total_geral)
        if i == 1:
            continue
        tempos_leitura.append(t_leit)
        tempos_proc.append(t_proc)
        tempos_total.append(t_total)
        linhas_lidas.append(n_rows)

    med = lambda lst: sum(lst) / len(lst)
    print(f"\n  --- Médias das execuções 2 a 5 ---")
    print(f"  Linhas lidas     : {med(linhas_lidas):.1f}")
    print(f"  Tempo leitura    : {med(tempos_leitura):.4f} s")
    print(f"  Tempo processam. : {med(tempos_proc):.4f} s")
    print(f"  Tempo total      : {med(tempos_total):.4f} s")

    return {
        "modelo":          modelo,
        "media_t_leitura": med(tempos_leitura),
        "media_t_proc":    med(tempos_proc),
        "media_t_total":   med(tempos_total),
        "media_linhas":    med(linhas_lidas),
    }, resultado_final


def imprimir_resultado_analitico(modelo, medias, venc_por_ano, venc_geral, total_geral, estados, anos):
    print(f"\n{'='*55}")
    print(f"  RESULTADO ANALÍTICO — {modelo}")
    print(f"{'='*55}")
    print(f"\n  {'Ano':<10}" + "".join(f"{est:>10}" for est in estados))
    print("  " + "-" * (10 + 10 * len(estados)))
    for ano in anos:
        linha = f"  {ano:<10}"
        for estado in estados:
            val = medias.get((estado, ano))
            linha += f"{val:>10.4f}" if val is not None else f"{'N/A':>10}"
        print(linha)
    print("\n  Vencedor por ano:")
    for ano in anos:
        estado, media = venc_por_ano[ano]
        print(f"    {ano}: {estado} ({media:.4f} mm)" if estado else f"    {ano}: sem dados")
    print("\n  Médias gerais (2000–2020):")
    for estado in estados:
        val = total_geral.get(estado)
        print(f"    {estado}: {val:.4f} mm" if val else f"    {estado}: N/A")
    vn, vm = venc_geral
    if vn:
        print(f"\n  *** Estado vencedor geral: {vn} com média de {vm:.4f} mm ***")


def salvar_csv(resultados, medias, venc_por_ano, venc_geral, total_geral, estados, anos):
    os.makedirs("results", exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["modelo","media_linhas_lidas","media_tempo_leitura_s",
                          "media_tempo_processamento_s","media_tempo_total_s"])
        for r in resultados:
            writer.writerow([r["modelo"], f"{r['media_linhas']:.1f}",
                              f"{r['media_t_leitura']:.4f}", f"{r['media_t_proc']:.4f}",
                              f"{r['media_t_total']:.4f}"])
    csv_analitico = "results/read_resultado_analitico.csv"
    with open(csv_analitico, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ano","estado","media_precipitacao_mm"])
        for ano in anos:
            for estado in estados:
                val = medias.get((estado, ano))
                writer.writerow([ano, estado, f"{val:.4f}" if val else "N/A"])
        vn, vm = venc_geral
        writer.writerow([])
        writer.writerow(["vencedor_geral", vn, f"{vm:.4f}" if vm else "N/A"])
    print(f"\n  Benchmark salvo em: {CSV_OUT}")
    print(f"  Resultado analítico salvo em: {csv_analitico}")


# =============================================================
print("=== READ DATA — BENCHMARK DE LEITURA ===\n")
print("Pergunta analítica:")
print("  Qual estado do Centro-Oeste teve maior precipitação média anual")
print("  ao longo de 2000–2020?\n")
print("Hipótese:")
print("  Modelo A (partição anual, menos roundtrips) vs.")
print("  Modelo B (partição mensal, mais roundtrips).")
print("  A granularidade da partition key afeta o tempo total de leitura")
print("  para consultas de longo período.\n")

cluster = Cluster(["127.0.0.1"])
session = cluster.connect(KEYSPACE)

stmt_a = session.prepare("""
    SELECT estado, ano, precipitacao
    FROM clima_modelo_a
    WHERE ano = ? AND estado = ?
""")

stmt_b = session.prepare("""
    SELECT estado, precipitacao
    FROM clima_modelo_b
    WHERE estado = ? AND ano_mes = ?
""")

bench_a, res_a = executar_benchmark(session, "Modelo A", buscar_modelo_a, processar_resultado_a, stmt_a, ESTADOS, ANOS)
medias_a, vpa, vga, tga = res_a
imprimir_resultado_analitico("Modelo A", medias_a, vpa, vga, tga, ESTADOS, ANOS)

bench_b, res_b = executar_benchmark(session, "Modelo B", buscar_modelo_b, processar_resultado_b, stmt_b, ESTADOS, ANOS)
medias_b, vpb, vgb, tgb = res_b
imprimir_resultado_analitico("Modelo B", medias_b, vpb, vgb, tgb, ESTADOS, ANOS)

print("\n" + "="*55)
print("  COMPARATIVO FINAL")
print("="*55)
print(f"\n  {'Métrica':<38} {'Modelo A':>10} {'Modelo B':>10}")
print("  " + "-"*60)
print(f"  {'Linhas lidas (média)':<38} {bench_a['media_linhas']:>10.1f} {bench_b['media_linhas']:>10.1f}")
print(f"  {'Tempo leitura Cassandra (s)':<38} {bench_a['media_t_leitura']:>10.4f} {bench_b['media_t_leitura']:>10.4f}")
print(f"  {'Tempo processamento Python (s)':<38} {bench_a['media_t_proc']:>10.4f} {bench_b['media_t_proc']:>10.4f}")
print(f"  {'Tempo total (s)':<38} {bench_a['media_t_total']:>10.4f} {bench_b['media_t_total']:>10.4f}")
fator = bench_b["media_t_leitura"] / bench_a["media_t_leitura"]
print(f"\n  Fator B/A: {fator:.2f}x  (>1 = Modelo B mais lento)")

vna, vma = vga
vnb, vmb = vgb
print(f"\n  Vencedor geral Modelo A: {vna} ({vma:.4f} mm)" if vna else "  Modelo A: sem dados")
print(f"  Vencedor geral Modelo B: {vnb} ({vmb:.4f} mm)" if vnb else "  Modelo B: sem dados")

salvar_csv([bench_a, bench_b], medias_a, vpa, vga, tga, ESTADOS, ANOS)
cluster.shutdown()
print("\nConexão encerrada.")