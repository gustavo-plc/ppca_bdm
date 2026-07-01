import time
from statistics import mean

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

# =========================================================
# CONFIGURAÇÃO GERAL
# =========================================================

KEYSPACE = "inmet"
TABELA_A = "clima_modelo_a"
TABELA_B = "clima_modelo_b"

NUM_RUNS = 5  # total de execuções; a primeira será descartada

ESTADOS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO"
]

# =========================================================
# ESCOLHA DO CENÁRIO
# =========================================================
# Opções:
#   MODE = "SEMESTRE_2005"
#   MODE = "CUSTOM"
# =========================================================

MODE = "CUSTOM"

# ---------------------------------------------------------
# CENÁRIO PRONTO
# ---------------------------------------------------------
SEMESTRE_2005_MONTHS = [7, 8, 9, 10, 11, 12]
SEMESTRE_2005_YEARS = [2005]
SEMESTRE_2005_HOUR_START = 12
SEMESTRE_2005_HOUR_END = 18

# ---------------------------------------------------------
# CENÁRIO CUSTOMIZÁVEL
# ---------------------------------------------------------
# Ajuste livremente estas variáveis para exagerar o cenário.
# Exemplos:
#   YEARS = [2005]
#   MONTHS = [11, 12]
#   HOUR_START = 12
#   HOUR_END = 15
#
#   YEARS = [2005, 2006]
#   MONTHS = [7, 8, 9, 10, 11, 12]
#   HOUR_START = 10
#   HOUR_END = 18
# ---------------------------------------------------------

YEARS = [2003, 2004]
MONTHS = [12]
HOUR_START = 4
HOUR_END = 22


def build_config():
    if MODE == "SEMESTRE_2005":
        years = SEMESTRE_2005_YEARS
        months = SEMESTRE_2005_MONTHS
        hour_start = SEMESTRE_2005_HOUR_START
        hour_end = SEMESTRE_2005_HOUR_END
    elif MODE == "CUSTOM":
        years = YEARS
        months = MONTHS
        hour_start = HOUR_START
        hour_end = HOUR_END
    else:
        raise ValueError("MODE inválido. Use 'SEMESTRE_2005' ou 'CUSTOM'.")

    if not years:
        raise ValueError("A lista YEARS não pode ser vazia.")
    if not months:
        raise ValueError("A lista MONTHS não pode ser vazia.")
    if hour_start > hour_end:
        raise ValueError("HOUR_START não pode ser maior que HOUR_END.")

    anos_meses_alvo = []
    for year in years:
        for month in months:
            anos_meses_alvo.append(f"{year}-{month:02d}")

    descricao = (
        f"Qual foi a temperatura média horária por estado "
        f"entre {hour_start}h e {hour_end}h, "
        f"nos meses {months} dos anos {years}?"
    )

    return {
        "years": years,
        "months": months,
        "hour_start": hour_start,
        "hour_end": hour_end,
        "anos_meses_alvo": anos_meses_alvo,
        "descricao": descricao
    }


def conectar_cassandra():
    cluster = Cluster(["127.0.0.1"])
    session = cluster.connect(KEYSPACE)
    return cluster, session


def consulta_modelo_a(session, cfg):
    """
    Modelo A:
    partition key = estado
    Filtra por ano, mes e hora dentro da partição com ALLOW FILTERING.
    """
    query = f"""
        SELECT estado, ano, mes, hora, temperatura_bulbo_seco
        FROM {TABELA_A}
        WHERE estado = %s
          AND ano = %s
          AND mes = %s
          AND hora >= %s
          AND hora <= %s
        ALLOW FILTERING
    """
    statement = SimpleStatement(query)

    soma_por_estado = {estado: 0.0 for estado in ESTADOS}
    contagem_por_estado = {estado: 0 for estado in ESTADOS}
    total_linhas = 0

    for estado in ESTADOS:
        for ano in cfg["years"]:
            for mes in cfg["months"]:
                rows = session.execute(
                    statement,
                    (estado, ano, mes, cfg["hour_start"], cfg["hour_end"])
                )
                for row in rows:
                    if row.temperatura_bulbo_seco is not None:
                        soma_por_estado[estado] += row.temperatura_bulbo_seco
                        contagem_por_estado[estado] += 1
                    total_linhas += 1

    medias = {}
    for estado in ESTADOS:
        qtd = contagem_por_estado[estado]
        medias[estado] = (soma_por_estado[estado] / qtd) if qtd > 0 else None

    return total_linhas, medias


def consulta_modelo_b(session, cfg):
    """
    Modelo B:
    partition key = (estado, ano_mes)
    Lê as partições corretas e filtra hora na aplicação.
    """
    query = f"""
        SELECT estado, ano_mes, hora, temperatura_bulbo_seco
        FROM {TABELA_B}
        WHERE estado = %s
          AND ano_mes = %s
    """
    statement = SimpleStatement(query)

    soma_por_estado = {estado: 0.0 for estado in ESTADOS}
    contagem_por_estado = {estado: 0 for estado in ESTADOS}
    total_linhas = 0

    for estado in ESTADOS:
        for ano_mes in cfg["anos_meses_alvo"]:
            rows = session.execute(statement, (estado, ano_mes))
            for row in rows:
                if row.hora is not None and cfg["hour_start"] <= row.hora <= cfg["hour_end"]:
                    if row.temperatura_bulbo_seco is not None:
                        soma_por_estado[estado] += row.temperatura_bulbo_seco
                        contagem_por_estado[estado] += 1
                    total_linhas += 1

    medias = {}
    for estado in ESTADOS:
        qtd = contagem_por_estado[estado]
        medias[estado] = (soma_por_estado[estado] / qtd) if qtd > 0 else None

    return total_linhas, medias


def benchmark_modelo(nome_modelo, func_consulta, session, cfg):
    tempos = []
    resultados = []

    print(f"\n=== BENCHMARK {nome_modelo} ===")

    for i in range(NUM_RUNS):
        inicio = time.perf_counter()
        linhas, medias = func_consulta(session, cfg)
        fim = time.perf_counter()

        duracao = fim - inicio
        tempos.append(duracao)
        resultados.append((linhas, medias))

        exemplos = {k: v for k, v in medias.items() if v is not None}
        exemplos_items = list(exemplos.items())[:5]
        exemplos_str = ", ".join([f"{uf}={temp:.3f}" for uf, temp in exemplos_items])

        print(
            f"Execução {i + 1}: tempo = {duracao:.3f} s, "
            f"linhas = {linhas}, "
            f"exemplos de médias = {exemplos_str}"
        )

    tempos_validos = tempos[1:]
    linhas_validas = [r[0] for r in resultados[1:]]
    medias_finais = resultados[-1][1]

    tempo_medio = mean(tempos_validos) if tempos_validos else None
    linhas_medias = mean(linhas_validas) if linhas_validas else None

    print(f"\n=== RESUMO {nome_modelo} (descartando a primeira execução) ===")
    print(f"Tempo médio (s)          : {tempo_medio:.3f}" if tempo_medio is not None else "Tempo médio (s): None")
    print(f"Linhas médias retornadas : {linhas_medias:.1f}" if linhas_medias is not None else "Linhas médias: None")

    return tempo_medio, linhas_medias, medias_finais


def imprimir_medias(medias, titulo):
    print(f"\n=== {titulo} ===")
    for estado in sorted(medias.keys()):
        valor = medias[estado]
        if valor is None:
            print(f"{estado}: sem dados")
        else:
            print(f"{estado}: {valor:.3f} °C")


def main():
    cfg = build_config()

    print("=== READ DATA 2 — LEITURA DE DADOS ===")
    print("Pergunta analítica:")
    print(cfg["descricao"])
    print("\nConfiguração:")
    print(f"MODE            : {MODE}")
    print(f"YEARS           : {cfg['years']}")
    print(f"MONTHS          : {cfg['months']}")
    print(f"HOUR_START      : {cfg['hour_start']}")
    print(f"HOUR_END        : {cfg['hour_end']}")
    print(f"ANO_MES ALVO    : {cfg['anos_meses_alvo']}")
    print(f"TOTAL PARTIÇÕES B POR ESTADO: {len(cfg['anos_meses_alvo'])}")

    cluster, session = conectar_cassandra()

    try:
        tempo_a, linhas_a, medias_a = benchmark_modelo("MODELO A", consulta_modelo_a, session, cfg)
        tempo_b, linhas_b, medias_b = benchmark_modelo("MODELO B", consulta_modelo_b, session, cfg)

        print("\n=== COMPARAÇÃO FINAL ===")
        print(f"Tempo médio MODELO A (s): {tempo_a:.3f}" if tempo_a is not None else "Tempo médio MODELO A: None")
        print(f"Tempo médio MODELO B (s): {tempo_b:.3f}" if tempo_b is not None else "Tempo médio MODELO B: None")
        print(f"Linhas médias A: {linhas_a:.1f}" if linhas_a is not None else "Linhas médias A: None")
        print(f"Linhas médias B: {linhas_b:.1f}" if linhas_b is not None else "Linhas médias B: None")

        if tempo_a is not None and tempo_b is not None and tempo_b > 0:
            print(f"Relação A/B: {tempo_a / tempo_b:.3f}")

        imprimir_medias(medias_a, "MÉDIAS POR ESTADO — MODELO A")
        imprimir_medias(medias_b, "MÉDIAS POR ESTADO — MODELO B")

    finally:
        print("\nEncerrando conexão com Cassandra...")
        cluster.shutdown()
        print("Conexão encerrada.")


if __name__ == "__main__":
    main()