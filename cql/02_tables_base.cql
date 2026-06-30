USE inmet;

CREATE TABLE IF NOT EXISTS clima_modelo_a (
    ano        int,
    estado     text,
    data_hora  timestamp,
    ano_mes    text,
    dia        int,
    hora       int,
    mes        int,
    ponto_de_orvalho         double,
    precipitacao             double,
    pressao                  double,
    radiacao                 double,
    temperatura_bulbo_seco   double,
    umidade                  int,
    vento_direcao            double,
    vento_rajada             double,
    vento_velocidade         double,
    PRIMARY KEY (ano, estado, data_hora)
) WITH CLUSTERING ORDER BY (estado ASC, data_hora ASC);

CREATE TABLE IF NOT EXISTS clima_modelo_b (
    estado     text,
    ano_mes    text,
    data_hora  timestamp,
    ano        int,
    dia        int,
    hora       int,
    mes        int,
    ponto_de_orvalho         double,
    precipitacao             double,
    pressao                  double,
    radiacao                 double,
    temperatura_bulbo_seco   double,
    umidade                  int,
    vento_direcao            double,
    vento_rajada             double,
    vento_velocidade         double,
    PRIMARY KEY ((estado, ano_mes), data_hora)
) WITH CLUSTERING ORDER BY (data_hora ASC);