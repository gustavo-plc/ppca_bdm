import time
import csv
import os
from cassandra.cluster import Cluster

KEYSPACE = "inmet"
ESTADOS = ["GO", "DF", "MT", "MS"]
ANOS = list(range(2000, 2021))
N_RUNS = 5

BENCHMARK_CSV = "results/read_benchmark_results.csv"
ANALYTIC_CSV = "results/read_resultado_analitico.csv"


def buscar_dados_mesma_query(session, stmt, tabela_nome):
    """
    Executa a MESMA estrutura de query nos dois modelos:
    SELECT estado, ano, precipitacao
    FROM <tabela>
    WHERE estado = ? AND ano = ? ALLOW FILTERING

    No Modelo A, essa query é compatível com a modelagem.
    No Modelo B, ela é inadequada e depende de ALLOW FILTERING.
    """
    rows_total = []

    for estado in ESTADOS:
        for ano in ANOS:
            result = list(session.execute(stmt, (estado, ano)))
            rows_total.extend(result)

    return rows_total


def processar_resultado(rows):
    """
    Calcula:
    - média anual de precipitação por estado
    - vencedor por ano
    - vencedor geral
    """
    acumulado = {
        (estado, ano): {"soma": 0.0, "count": 0}
        for estado in ESTADOS
        for ano in ANOS
    }

    for row in rows:
        try:
            estado = row.estado
            ano = int(row.ano)
            precipitacao = row.precipitacao
        except Exception:
            continue

        if estado in ESTADOS and ano in ANOS and precipitacao is not None:
            acumulado[(estado, ano)]["soma"] += precipitacao
            acumulado[(estado, ano)]["count"] += 1

    medias = {}
    for (estado, ano), valores in acumulado.items():
        if valores["count"] > 0:
            medias[(estado, ano)] = valores["soma"] / valores["count"]
        else:
            medias[(estado, ano)] = None

    vencedores_por_ano = {}
    for ano in ANOS:
        melhor_estado = None
        melhor_media = -1

        for estado in ESTADOS:
            media = medias[(estado, ano)]
            if media is not None and media > melhor_media:
                melhor_estado = estado
                melhor_media = media

        vencedores_por_ano[ano] = (melhor_estado, melhor_media if melhor_estado else None)

    medias_gerais = {}
    for estado in ESTADOS:
        valores = [
            medias[(estado, ano)]
            for ano in ANOS
            if medias[(estado, ano)] is not None
        ]
        medias_gerais[estado] = sum(valores) / len(valores) if valores else None

    vencedor_geral = None
    melhor_media_geral = -1
    for estado, media in medias_gerais.items():
        if media is not None and media > melhor_media_geral:
            vencedor_geral = estado
            melhor_media_geral = media

    return medias, vencedores_por_ano, medias_gerais, vencedor_geral, melhor_media_geral


def executar_benchmark(session, modelo_nome, stmt):
    tempos_leitura = []
    tempos_processamento = []
    tempos_totais = []
    linhas_lidas = []

    ultimo_resultado = None

    print(f"\n{'=' * 55}")
    print(f"  BENCHMARK DE LEITURA — {modelo_nome}")
    print(f"{'=' * 55}")

    for i in range(1, N_RUNS + 1):
        descartada = " [DESCARTADA]" if i == 1 else ""
        print(f"  Execução {i}/{N_RUNS}{descartada}")

        t0 = time.time()
        rows = buscar_dados_mesma_query(session, stmt, modelo_nome)
        t1 = time.time()

        resultado = processar_resultado(rows)
        t2 = time.time()

        tempo_leitura = t1 - t0
        tempo_processamento = t2 - t1
        tempo_total = t2 - t0
        n_rows = len(rows)

        print(f"    Linhas lidas     : {n_rows}")
        print(f"    Tempo leitura    : {tempo_leitura:.4f} s")
        print(f"    Tempo processam. : {tempo_processamento:.4f} s")
        print(f"    Tempo total      : {tempo_total:.4f} s")

        ultimo_resultado = resultado

        if i == 1:
            continue

        tempos_leitura.append(tempo_leitura)
        tempos_processamento.append(tempo_processamento)
        tempos_totais.append(tempo_total)
        linhas_lidas.append(n_rows)

    media_leitura = sum(tempos_leitura) / len(tempos_leitura)
    media_processamento = sum(tempos_processamento) / len(tempos_processamento)
    media_total = sum(tempos_totais) / len(tempos_totais)
    media_linhas = sum(linhas_lidas) / len(linhas_lidas)

    print(f"\n  --- Médias das execuções 2 a 5 ---")
    print(f"  Linhas lidas     : {media_linhas:.1f}")
    print(f"  Tempo leitura    : {media_leitura:.4f} s")
    print(f"  Tempo processam. : {media_processamento:.4f} s")
    print(f"  Tempo total      : {media_total:.4f} s")

    return {
        "modelo": modelo_nome,
        "media_linhas": media_linhas,
        "media_t_leitura": media_leitura,
        "media_t_processamento": media_processamento,
        "media_t_total": media_total,
        "resultado_analitico": ultimo_resultado
    }


def imprimir_resultado_analitico(modelo_nome, resultado):
    medias, vencedores_por_ano, medias_gerais, vencedor_geral, melhor_media_geral = resultado

    print(f"\n{'=' * 55}")
    print(f"  RESULTADO ANALÍTICO — {modelo_nome}")
    print(f"{'=' * 55}")

    print(f"\n  {'Ano':<10}" + "".join(f"{estado:>10}" for estado in ESTADOS))
    print("  " + "-" * (10 + 10 * len(ESTADOS)))

    for ano in ANOS:
        linha = f"  {ano:<10}"
        for estado in ESTADOS:
            media = medias[(estado, ano)]
            linha += f"{media:>10.4f}" if media is not None else f"{'N/A':>10}"
        print(linha)

    print("\n  Vencedor por ano:")
    for ano in ANOS:
        estado, media = vencedores_por_ano[ano]
        if estado is not None:
            print(f"    {ano}: {estado} ({media:.4f} mm)")
        else:
            print(f"    {ano}: sem dados")

    print("\n  Médias gerais (2000–2020):")
    for estado in ESTADOS:
        media = medias_gerais[estado]
        if media is not None:
            print(f"    {estado}: {media:.4f} mm")
        else:
            print(f"    {estado}: N/A")

    if vencedor_geral is not None:
        print(f"\n  *** Estado vencedor geral: {vencedor_geral} com média de {melhor_media_geral:.4f} mm ***")
    else:
        print("\n  *** Sem vencedor geral (sem dados) ***")


def salvar_resultados_csv(benchmark_a, benchmark_b):
    os.makedirs("results", exist_ok=True)

    with open(BENCHMARK_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "modelo",
            "media_linhas_lidas",
            "media_tempo_leitura_s",
            "media_tempo_processamento_s",
            "media_tempo_total_s"
        ])
        for bench in [benchmark_a, benchmark_b]:
            writer.writerow([
                bench["modelo"],
                f"{bench['media_linhas']:.1f}",
                f"{bench['media_t_leitura']:.4f}",
                f"{bench['media_t_processamento']:.4f}",
                f"{bench['media_t_total']:.4f}"
            ])

    resultado_a = benchmark_a["resultado_analitico"]
    medias_a, vencedores_por_ano_a, medias_gerais_a, vencedor_geral_a, melhor_media_geral_a = resultado_a

    with open(ANALYTIC_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ano", "estado", "media_precipitacao_mm"])
        for ano in ANOS:
            for estado in ESTADOS:
                media = medias_a[(estado, ano)]
                writer.writerow([
                    ano,
                    estado,
                    f"{media:.4f}" if media is not None else "N/A"
                ])

        writer.writerow([])
        writer.writerow(["estado_vencedor_geral", vencedor_geral_a])
        writer.writerow(["media_vencedor_geral_mm", f"{melhor_media_geral_a:.4f}" if melhor_media_geral_a is not None else "N/A"])

    print(f"\n  Benchmark salvo em: {BENCHMARK_CSV}")
    print(f"  Resultado analítico salvo em: {ANALYTIC_CSV}")


print("=== READ DATA — BENCHMARK DE LEITURA (MESMA QUERY) ===\n")
print("Pergunta analítica:")
print("  Qual estado do Centro-Oeste teve maior precipitação média anual")
print("  ao longo de 2000–2020?\n")

print("Estratégia experimental:")
print("  A MESMA estrutura de query será aplicada aos dois modelos:")
print("  SELECT estado, ano, precipitacao")
print("  FROM <tabela>")
print("  WHERE estado = ? AND ano = ? ALLOW FILTERING\n")

print("Objetivo:")
print("  Comparar o efeito de aplicar a mesma consulta lógica")
print("  sobre duas modelagens com chaves de partição diferentes.\n")

print("Conectando ao Cassandra...")
cluster = Cluster(["127.0.0.1"])
session = cluster.connect(KEYSPACE)

stmt_a = session.prepare("""
    SELECT estado, ano, precipitacao
    FROM clima_modelo_a
    WHERE estado = ? AND ano = ? ALLOW FILTERING
""")

stmt_b = session.prepare("""
    SELECT estado, ano, precipitacao
    FROM clima_modelo_b
    WHERE estado = ? AND ano = ? ALLOW FILTERING
""")

benchmark_a = executar_benchmark(session, "Modelo A", stmt_a)
imprimir_resultado_analitico("Modelo A", benchmark_a["resultado_analitico"])

benchmark_b = executar_benchmark(session, "Modelo B", stmt_b)
imprimir_resultado_analitico("Modelo B", benchmark_b["resultado_analitico"])

print("\n" + "=" * 55)
print("  COMPARATIVO FINAL")
print("=" * 55)

print(f"\n  {'Métrica':<38} {'Modelo A':>10} {'Modelo B':>10}")
print("  " + "-" * 60)
print(f"  {'Linhas lidas (média)':<38} {benchmark_a['media_linhas']:>10.1f} {benchmark_b['media_linhas']:>10.1f}")
print(f"  {'Tempo leitura Cassandra (s)':<38} {benchmark_a['media_t_leitura']:>10.4f} {benchmark_b['media_t_leitura']:>10.4f}")
print(f"  {'Tempo processamento Python (s)':<38} {benchmark_a['media_t_processamento']:>10.4f} {benchmark_b['media_t_processamento']:>10.4f}")
print(f"  {'Tempo total (s)':<38} {benchmark_a['media_t_total']:>10.4f} {benchmark_b['media_t_total']:>10.4f}")

if benchmark_a["media_t_leitura"] > 0:
    fator = benchmark_b["media_t_leitura"] / benchmark_a["media_t_leitura"]
    print(f"\n  Fator B/A: {fator:.2f}x  (>1 = Modelo B mais lento; <1 = Modelo B mais rápido)")

resultado_a = benchmark_a["resultado_analitico"]
resultado_b = benchmark_b["resultado_analitico"]

_, _, medias_gerais_a, vencedor_geral_a, melhor_media_geral_a = resultado_a
_, _, medias_gerais_b, vencedor_geral_b, melhor_media_geral_b = resultado_b

if vencedor_geral_a is not None:
    print(f"\n  Vencedor geral Modelo A: {vencedor_geral_a} ({melhor_media_geral_a:.4f} mm)")
else:
    print("\n  Modelo A: sem vencedor geral")

if vencedor_geral_b is not None:
    print(f"  Vencedor geral Modelo B: {vencedor_geral_b} ({melhor_media_geral_b:.4f} mm)")
else:
    print("  Modelo B: sem vencedor geral")

salvar_resultados_csv(benchmark_a, benchmark_b)

cluster.shutdown()
print("\nConexão encerrada.")