import time
from statistics import mean

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

KEYSPACE = "inmet"
TABELA_A = "clima_modelo_a"
TABELA_B = "clima_modelo_b"

NUM_RUNS = 5  # descartar a primeira
ESTADOS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO"
]

ANOS_MESES = [
    "2000-05", "2000-06", "2000-07", "2000-08", "2000-09", "2000-10", "2000-11", "2000-12",
    "2001-01", "2001-02", "2001-03", "2001-04", "2001-05", "2001-06", "2001-07", "2001-08",
    "2001-09", "2001-10", "2001-11", "2001-12", "2002-01", "2002-02", "2002-03", "2002-04",
    "2002-05", "2002-06", "2002-07", "2002-08", "2002-09", "2002-10", "2002-11", "2002-12",
    "2003-01", "2003-02", "2003-03", "2003-04", "2003-05", "2003-06", "2003-07", "2003-08",
    "2003-09", "2003-10", "2003-11", "2003-12", "2004-01", "2004-02", "2004-03", "2004-04",
    "2004-05", "2004-06", "2004-07", "2004-08", "2004-09", "2004-10", "2004-11", "2004-12",
    "2005-01", "2005-02", "2005-03", "2005-04", "2005-05", "2005-06", "2005-07", "2005-08",
    "2005-09", "2005-10", "2005-11", "2005-12", "2006-01", "2006-02", "2006-03", "2006-04",
    "2006-05", "2006-06", "2006-07", "2006-08", "2006-09", "2006-10", "2006-11", "2006-12",
    "2007-01", "2007-02", "2007-03", "2007-04", "2007-05", "2007-06", "2007-07", "2007-08",
    "2007-09", "2007-10", "2007-11", "2007-12", "2008-01", "2008-02", "2008-03", "2008-04",
    "2008-05", "2008-06", "2008-07", "2008-08", "2008-09", "2008-10", "2008-11", "2008-12",
    "2009-01", "2009-02", "2009-03", "2009-04", "2009-05", "2009-06", "2009-07", "2009-08",
    "2009-09", "2009-10", "2009-11", "2009-12", "2010-01", "2010-02", "2010-03", "2010-04",
    "2010-05", "2010-06", "2010-07", "2010-08", "2010-09", "2010-10", "2010-11", "2010-12",
    "2011-01", "2011-02", "2011-03", "2011-04", "2011-05", "2011-06", "2011-07", "2011-08",
    "2011-09", "2011-10", "2011-11", "2011-12", "2012-01", "2012-02", "2012-03", "2012-04",
    "2012-05", "2012-06", "2012-07", "2012-08", "2012-09", "2012-10", "2012-11", "2012-12",
    "2013-01", "2013-02", "2013-03", "2013-04", "2013-05", "2013-06", "2013-07", "2013-08",
    "2013-09", "2013-10", "2013-11", "2013-12", "2014-01", "2014-02", "2014-03", "2014-04",
    "2014-05", "2014-06", "2014-07", "2014-08", "2014-09", "2014-10", "2014-11", "2014-12",
    "2015-01", "2015-02", "2015-03", "2015-04", "2015-05", "2015-06", "2015-07", "2015-08",
    "2015-09", "2015-10", "2015-11", "2015-12", "2016-01", "2016-02", "2016-03", "2016-04",
    "2016-05", "2016-06", "2016-07", "2016-08", "2016-09", "2016-10", "2016-11", "2016-12",
    "2017-01", "2017-02", "2017-03", "2017-04", "2017-05", "2017-06", "2017-07", "2017-08",
    "2017-09", "2017-10", "2017-11", "2017-12", "2018-01", "2018-02", "2018-03", "2018-04",
    "2018-05", "2018-06", "2018-07", "2018-08", "2018-09", "2018-10", "2018-11", "2018-12",
    "2019-01", "2019-02", "2019-03", "2019-04", "2019-05", "2019-06", "2019-07", "2019-08",
    "2019-09", "2019-10", "2019-11", "2019-12", "2020-01", "2020-02", "2020-03", "2020-04",
    "2020-05", "2020-06", "2020-07", "2020-08", "2020-09", "2020-10", "2020-11", "2020-12"
]


def conectar_cassandra():
    cluster = Cluster(["127.0.0.1"])
    session = cluster.connect(KEYSPACE)
    return cluster, session


def consulta_modelo_a(session):
    query = f"""
        SELECT estado, temperatura_bulbo_seco
        FROM {TABELA_A}
        WHERE estado = %s
        ALLOW FILTERING
    """
    statement = SimpleStatement(query)

    soma_por_estado = {estado: 0.0 for estado in ESTADOS}
    contagem_por_estado = {estado: 0 for estado in ESTADOS}
    total_linhas = 0

    for estado in ESTADOS:
        rows = session.execute(statement, (estado,))
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
    query = f"""
        SELECT estado, temperatura_bulbo_seco
        FROM {TABELA_B}
        WHERE estado = %s
          AND ano_mes = %s
    """
    statement = SimpleStatement(query)

    soma_por_estado = {estado: 0.0 for estado in ESTADOS}
    contagem_por_estado = {estado: 0 for estado in ESTADOS}
    total_linhas = 0

    for estado in ESTADOS:
        for ano_mes in ANOS_MESES:
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
    print("=== READ DATA — LEITURA DE DADOS ===")
    print("Pergunta analítica:")
    print("Qual é a temperatura média horária por estado, ao longo de todo o período disponível na base?")

    cluster, session = conectar_cassandra()

    try:
        tempo_a, linhas_a, medias_a = benchmark_modelo("MODELO A", consulta_modelo_a, session)
        tempo_b, linhas_b, medias_b = benchmark_modelo("MODELO B", consulta_modelo_b, session)

        print("\n=== COMPARAÇÃO FINAL ===")
        print(f"Tempo médio MODELO A (s): {tempo_a:.3f}" if tempo_a is not None else "Tempo médio MODELO A: None")
        print(f"Tempo médio MODELO B (s): {tempo_b:.3f}" if tempo_b is not None else "Tempo médio MODELO B: None")
        print(f"Linhas médias A: {linhas_a:.1f}" if linhas_a is not None else "Linhas médias A: None")
        print(f"Linhas médias B: {linhas_b:.1f}" if linhas_b is not None else "Linhas médias B: None")

        imprimir_medias(medias_a, "MÉDIAS POR ESTADO — MODELO A")
        imprimir_medias(medias_b, "MÉDIAS POR ESTADO — MODELO B")

    finally:
        print("\nEncerrando conexão com Cassandra...")
        cluster.shutdown()
        print("Conexão encerrada.")


if __name__ == "__main__":
    main()