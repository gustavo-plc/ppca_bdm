import time
from statistics import mean

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

KEYSPACE = "inmet"
TABELA_A = "clima_modelo_a"
TABELA_B = "clima_modelo_b"

NUM_RUNS = 5  # descartar a primeira
ANO_ALVO = 2005

ESTADOS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO"
]

ANOS_MESES_2005 = [
    "2005-01", "2005-02", "2005-03", "2005-04",
    "2005-05", "2005-06", "2005-07", "2005-08",
    "2005-09", "2005-10", "2005-11", "2005-12"
]


def conectar_cassandra():
    cluster = Cluster(["127.0.0.1"])
    session = cluster.connect(KEYSPACE)
    return cluster, session


def consulta_modelo_a(session):
    """
    Pergunta analítica:
    Qual foi a temperatura média horária por estado ao longo de 2005?

    Modelo A:
    partition key = estado
    Para responder por estado em 2005, precisamos filtrar por ano dentro
    da partição, usando ALLOW FILTERING.
    """
    query = f"""
        SELECT estado, ano, temperatura_bulbo_seco
        FROM {TABELA_A}
        WHERE estado = %s
          AND ano = %s
        ALLOW FILTERING
    """
    statement = SimpleStatement(query)

    soma_por_estado = {estado: 0.0 for estado in ESTADOS}
    contagem_por_estado = {estado: 0 for estado in ESTADOS}
    total_linhas = 0

    for estado in ESTADOS:
        rows = session.execute(statement, (estado, ANO_ALVO))
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


def consulta_modelo_b(session):
    """
    Pergunta analítica:
    Qual foi a temperatura média horária por estado ao longo de 2005?

    Modelo B:
    partition key = (estado, ano_mes)
    A consulta fica naturalmente alinhada ao particionamento, lendo
    12 partições por estado.
    """
    query = f"""
        SELECT estado, ano_mes, temperatura_bulbo_seco
        FROM {TABELA_B}
        WHERE estado = %s
          AND ano_mes = %s
    """
    statement = SimpleStatement(query)

    soma_por_estado = {estado: 0.0 for estado in ESTADOS}
    contagem_por_estado = {estado: 0 for estado in ESTADOS}
    total_linhas = 0

    for estado in ESTADOS:
        for ano_mes in ANOS_MESES_2005:
            rows = session.execute(statement, (estado, ano_mes))
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


def benchmark_modelo(nome_modelo, func_consulta, session):
    tempos = []
    resultados = []

    print(f"\n=== BENCHMARK {nome_modelo} ===")

    for i in range(NUM_RUNS):
        inicio = time.perf_counter()
        linhas, medias = func_consulta(session)
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
    print("=== READ DATA 2 — LEITURA DE DADOS ===")
    print("Pergunta analítica:")
    print("Qual foi a temperatura média horária por estado ao longo de 2005?")

    cluster, session = conectar_cassandra()

    try:
        tempo_a, linhas_a, medias_a = benchmark_modelo("MODELO A", consulta_modelo_a, session)
        tempo_b, linhas_b, medias_b = benchmark_modelo("MODELO B", consulta_modelo_b, session)

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