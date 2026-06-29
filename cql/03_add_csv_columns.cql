USE inmet;

-- =========================
-- MODELO A
-- PRIMARY KEY (ano, estado, data_hora)
-- Colunas adicionais
-- =========================
ALTER TABLE clima_modelo_a ADD mes int;
ALTER TABLE clima_modelo_a ADD dia int;
ALTER TABLE clima_modelo_a ADD hora int;
ALTER TABLE clima_modelo_a ADD precipitacao double;
ALTER TABLE clima_modelo_a ADD pressao double;
ALTER TABLE clima_modelo_a ADD radiacao double;
ALTER TABLE clima_modelo_a ADD temperatura_bulbo_seco double;
ALTER TABLE clima_modelo_a ADD ponto_de_orvalho double;
ALTER TABLE clima_modelo_a ADD umidade int;
ALTER TABLE clima_modelo_a ADD vento_direcao double;
ALTER TABLE clima_modelo_a ADD vento_rajada double;
ALTER TABLE clima_modelo_a ADD vento_velocidade double;
ALTER TABLE clima_modelo_a ADD ano_mes text;

-- =========================
-- MODELO B
-- PRIMARY KEY ((estado, ano_mes), data_hora)
-- Colunas adicionais
-- =========================
ALTER TABLE clima_modelo_b ADD ano int;
ALTER TABLE clima_modelo_b ADD mes int;
ALTER TABLE clima_modelo_b ADD dia int;
ALTER TABLE clima_modelo_b ADD hora int;
ALTER TABLE clima_modelo_b ADD precipitacao double;
ALTER TABLE clima_modelo_b ADD pressao double;
ALTER TABLE clima_modelo_b ADD radiacao double;
ALTER TABLE clima_modelo_b ADD temperatura_bulbo_seco double;
ALTER TABLE clima_modelo_b ADD ponto_de_orvalho double;
ALTER TABLE clima_modelo_b ADD umidade int;
ALTER TABLE clima_modelo_b ADD vento_direcao double;
ALTER TABLE clima_modelo_b ADD vento_rajada double;
ALTER TABLE clima_modelo_b ADD vento_velocidade double;