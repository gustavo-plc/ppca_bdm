USE inmet;

-- =============================================================
-- MODELO A: Partição ingênua
-- Partition key: apenas "ano"
-- Problema: todas as ~1,3M de linhas de um mesmo ano ficam
-- na mesma partição → wide partition clássico
-- Referência anti-pattern: https://thelastpickle.com/blog/2019/01/11/wide-partitions-cassandra-3-11.html
-- =============================================================
CREATE TABLE IF NOT EXISTS clima_modelo_a (
    ano        int,
    estado     text,
    data_hora  timestamp,
    PRIMARY KEY (ano, estado, data_hora)
) WITH CLUSTERING ORDER BY (estado ASC, data_hora ASC);


-- =============================================================
-- MODELO B: Partição otimizada (Bucketing por estado + mês)
-- Partition key composta: (estado, ano_mes)
-- ano_mes é gerado no script Python como "AAAA-MM" (ex: "2020-11")
-- Resultado: ~4k linhas por partição
-- Referência best practice: DataStax, Apache Cassandra docs
-- =============================================================
CREATE TABLE IF NOT EXISTS clima_modelo_b (
    estado     text,
    ano_mes    text,
    data_hora  timestamp,
    PRIMARY KEY ((estado, ano_mes), data_hora)
) WITH CLUSTERING ORDER BY (data_hora ASC);