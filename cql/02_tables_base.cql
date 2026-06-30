USE inmet;

-- =============================================================
-- MODELO A: Partição ingênua — wide partition clássico
-- Partition key: apenas "estado" (baixa cardinalidade)
-- Problema: toda a série histórica de um estado acumula
-- na mesma partição → centenas de milhares de linhas por partição
-- Anti-pattern: baixa cardinalidade na partition key
-- Referência: https://thelastpickle.com/blog/2019/01/11/wide-partitions-cassandra-3-11.html
-- =============================================================
CREATE TABLE IF NOT EXISTS clima_modelo_a (
    estado                   text,
    data_hora                timestamp,
    ano                      int,
    mes                      int,
    dia                      int,
    hora                     int,
    ano_mes                  text,
    precipitacao             double,
    pressao                  double,
    radiacao                 double,
    temperatura_bulbo_seco   double,
    ponto_de_orvalho         double,
    umidade                  int,
    vento_direcao            double,
    vento_rajada             double,
    vento_velocidade         double,
    PRIMARY KEY (estado, data_hora)
) WITH CLUSTERING ORDER BY (data_hora ASC);


-- =============================================================
-- MODELO B: Partição otimizada — bucketing por estado + mês
-- Partition key composta: (estado, ano_mes)
-- Resultado: ~720 linhas por partição (24h × 30 dias)
-- Padrão: time bucketing recomendado para séries temporais
-- Referência: DataStax, Apache Cassandra docs
-- =============================================================
CREATE TABLE IF NOT EXISTS clima_modelo_b (
    estado                   text,
    ano_mes                  text,
    data_hora                timestamp,
    ano                      int,
    mes                      int,
    dia                      int,
    hora                     int,
    precipitacao             double,
    pressao                  double,
    radiacao                 double,
    temperatura_bulbo_seco   double,
    ponto_de_orvalho         double,
    umidade                  int,
    vento_direcao            double,
    vento_rajada             double,
    vento_velocidade         double,
    PRIMARY KEY ((estado, ano_mes), data_hora)
) WITH CLUSTERING ORDER BY (data_hora ASC);