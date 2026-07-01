| Item                  | Conteúdo                                                                                                           |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Título                | Modelagem de Dados e Desempenho de Leitura no Apache Cassandra: Um Estudo Experimental com Dados Climáticos        |
| Hipótese de pesquisa  | A modelagem do banco de dados influencia o desempenho de leitura a depender do tipo de query a ser executada       |
| Objeto de estudo      | Apache Cassandra — dois modelos de dados com diferentes estratégias de particionamento                             |
| Dados utilizados      | Dataset climático INMET, recorte temporal 2000–2020, cobertura nacional (27 UFs)                                   |
| Método                | Experimental — benchmark controlado com 3 cenários de consulta e 5 execuções por modelo (com descarte da primeira) |
| Variável independente | Estratégia de modelagem (partition key por estado vs. partition key por (estado, ano_mes))                         |
| Variável dependente   | Tempo médio de leitura (segundos)                                                                                  |
| Variável de controle  | Mesma pergunta analítica, mesmo volume de dados retornado, mesmo ambiente de execução                              |

***

## Configuração comum aos três scripts

| Parâmetro | Valor |
|---|---|
| Keyspace | `inmet` |
| Tabelas | `clima_modelo_a` / `clima_modelo_b` |
| Estados analisados | 27 UFs (cobertura nacional completa) |
| Execuções por modelo | 5, com descarte da primeira |
| Campo de medida | `temperatura_bulbo_seco` |
| Agregação | Calculada na aplicação (soma ÷ contagem), sem uso de `AVG` CQL |

***

## Os dois modelos de dados

| | Modelo A | Modelo B |
|---|---|---|
| **Partition key** | `estado` | `(estado, ano_mes)` |
| **Partição resultante** | Uma partição "wide" por estado, contendo todos os anos e meses | Uma partição "estreita" por estado + mês |
| **Característica** | Ótimo para agregar por estado em grandes janelas temporais | Ótimo para recortes temporais específicos por estado + mês |

***

## Os três experimentos

### `read_data1.py` — Agregação total no histórico

| Item | Detalhe |
|---|---|
| **Pergunta analítica** | Qual é a temperatura média horária por estado ao longo de todo o período disponível na base? |
| **Recorte temporal** | `2000-05` a `2020-12` — todo o intervalo disponível |
| **Recorte físico** | 27 estados, sem filtro de hora ou mês |
| **Query Modelo A** | `WHERE estado = ?` — 1 query por estado = **27 queries** |
| **Query Modelo B** | `WHERE estado = ? AND ano_mes = ?` — 1 query por `(estado, ano_mes)` = **~6.696 queries** |
| **Penalidade do Modelo A** | Nenhuma relevante — lê a partição inteira por estado, que é exatamente o que a pergunta exige |
| **Penalidade do Modelo B** | Overhead massivo: milhares de round-trips para agregar o histórico completo |
| **Vencedor esperado** | **Modelo A** |

***

### `read_data2.py` — Recorte temporal bem definido

| Item | Detalhe |
|---|---|
| **Pergunta analítica** | Qual foi a temperatura média horária por estado no segundo semestre de 2005? |
| **Recorte temporal** | Meses 7 a 12 de 2005 |
| **Recorte físico** | 27 estados, sem filtro de hora |
| **Query Modelo A** | `WHERE estado = ? AND ano = 2005 AND mes = ? ALLOW FILTERING` — **162 queries** |
| **Query Modelo B** | `WHERE estado = ? AND ano_mes = ?` — **162 queries** |
| **Penalidade do Modelo A** | `ALLOW FILTERING` em `ano` e `mes` dentro da partição `estado`, forçando scan interno |
| **Penalidade do Modelo B** | Nenhuma relevante — 6 partições bem alinhadas por estado |
| **Vencedor esperado** | **Modelo B** |

***

### `read_data3.py` — Cenário parametrizado (com filtro de hora)

| Item | Detalhe |
|---|---|
| **Pergunta analítica** | Qual foi a temperatura média horária por estado entre `<HOUR_START>`h e `<HOUR_END>`h, nos meses `<MONTHS>` dos anos `<YEARS>`? |
| **Recorte temporal** | Configurável via `YEARS`, `MONTHS`, `HOUR_START`, `HOUR_END` |
| **Recorte físico** | 27 estados |
| **Query Modelo A** | `WHERE estado = ? AND ano = ? AND mes = ? AND hora >= ? AND hora <= ? ALLOW FILTERING` |
| **Query Modelo B** | `WHERE estado = ? AND ano_mes = ?` — filtro de hora feito na aplicação |
| **Penalidade do Modelo A** | `ALLOW FILTERING` com múltiplos filtros desalinhados (`ano`, `mes`, `hora`), scan mais custoso |
| **Penalidade do Modelo B** | Cresce com o número de `ano_mes` no intervalo; acima de ~12–18 partições por estado, o overhead de queries começa a superar o ganho do alinhamento |
| **Vencedor esperado** | **Modelo B** em janelas curtas; **Modelo A** quando YEARS × MONTHS gera muitas partições |

***

## Conclusão sintetizada

Os três scripts demonstram empiricamente o princípio central da modelagem no Cassandra: **a eficiência não depende apenas de como os dados estão armazenados, mas de quão bem o padrão de acesso da query está alinhado ao particionamento da tabela**. [cassandra.apache](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html)

| Cenário | Quem ganha | Por quê |
|---|---|---|
| Agregação por estado em todo o histórico | **Modelo A** | A pergunta casa naturalmente com a partition key `estado`; o B precisa de milhares de queries |
| Recorte por estado + poucos meses | **Modelo B** | A pergunta casa com `(estado, ano_mes)`; o A precisa de `ALLOW FILTERING` |
| Recorte por estado + muitos meses + filtro de hora | **Modelo A** | O overhead de queries do B supera o custo do `ALLOW FILTERING` do A |

Essa inversão de desempenho entre cenários é o ponto mais rico discussão: não existe modelo "melhor" em Cassandra de forma absoluta — existe modelo mais adequado para um determinado padrão de consulta.

## 📊 Resultados dos Experimentos

### Configuração do Benchmark

| Parâmetro | Valor |
|---|---|
| Banco de dados | Apache Cassandra |
| Keyspace | `inmet` |
| Tabelas | `clima_modelo_a` / `clima_modelo_b` |
| Estados analisados | 27 UFs (cobertura nacional) |
| Execuções por modelo | 5 (primeira descartada) |
| Campo de medida | `temperatura_bulbo_seco` |
| Agregação | Calculada na aplicação (sem `AVG` CQL) |

---

### Modelos comparados

| | Modelo A | Modelo B |
|---|---|---|
| **Partition key** | `estado` | `(estado, ano_mes)` |
| **Partição** | Wide — um estado contém todo o histórico | Estreita — um estado + um mês por partição |
| **Queries por experimento** | Poucas (1 por estado ou 1 por estado+mês) | Muitas (1 por `estado × ano_mes`) |

---

### Experimento 1 — `read_data1.py`

> **Pergunta:** Qual é a temperatura média horária por estado ao longo de todo o período disponível na base?
> **Recorte temporal:** `2000-05` a `2020-12` (histórico completo)

| Modelo | Query | Nº de queries | Tempo médio | Linhas lidas |
|---|---|---|---|---|
| A | `WHERE estado = ?` | 27 | **1,567 s** ✅ | 287.227 |
| B | `WHERE estado = ? AND ano_mes = ?` | ~6.696 | 97,540 s | 287.227 |

**Relação A/B: 0,016 — Modelo A ~62× mais rápido**

> O Modelo A vence porque a pergunta agrega por estado em todo o histórico — padrão que casa perfeitamente com a partition key `estado`. O Modelo B precisou de ~6.696 queries para cobrir o mesmo período, gerando overhead massivo de round-trips.

---

### Experimento 2 — `read_data2.py`

> **Pergunta:** Qual foi a temperatura média horária por estado no segundo semestre de 2005?
> **Recorte temporal:** meses 7 a 12 de 2005

| Modelo | Query | Nº de queries | Tempo médio | Linhas lidas |
|---|---|---|---|---|
| A | `WHERE estado = ? AND ano = 2005 AND mes = ? ALLOW FILTERING` | 162 | 3,605 s | 45.528 |
| B | `WHERE estado = ? AND ano_mes = ?` | 162 | **2,479 s** ✅ | 45.528 |

**Relação A/B: 1,454 — Modelo B ~45% mais rápido**

> O Modelo B vence porque a partition key `(estado, ano_mes)` está alinhada ao recorte temporal da pergunta. O Modelo A precisou de `ALLOW FILTERING` para filtrar `ano` e `mes` dentro da partição `estado`, gerando scan interno desnecessário.

---

### Experimento 3 — `read_data3.py`

> **Pergunta:** Qual foi a temperatura média horária por estado entre 4h e 22h, no mês de dezembro dos anos 2003 e 2004?
> **Recorte temporal:** `2003-12` e `2004-12` | **Recorte horário:** 4h–22h

| Modelo | Query | Nº de queries | Tempo médio | Linhas lidas |
|---|---|---|---|---|
| A | `WHERE estado = ? AND ano = ? AND mes = ? AND hora >= ? AND hora <= ? ALLOW FILTERING` | 54 | 1,268 s | 10.310 |
| B | `WHERE estado = ? AND ano_mes = ?` + filtro de hora na aplicação | 54 | **0,824 s** ✅ | 10.310 |

**Relação A/B: 1,539 — Modelo B ~54% mais rápido**

> O Modelo B vence porque continua bem alinhado ao particionamento por `(estado, ano_mes)`. O Modelo A acumula múltiplos filtros desalinhados (`ano`, `mes`, `hora`) dentro da partition key `estado`, tornando o `ALLOW FILTERING` mais custoso que no Experimento 2.

---

### Resumo comparativo

| Experimento | Pergunta (síntese) | Linhas lidas | Tempo A | Tempo B | Vencedor |
|---|---|---|---|---|---|
| 1 | Média por estado — histórico completo | 287.227 | 1,567 s | 97,540 s | **Modelo A** |
| 2 | Média por estado — 2º semestre 2005 | 45.528 | 3,605 s | 2,479 s | **Modelo B** |
| 3 | Média por estado — dez/2003 e dez/2004, 4h–22h | 10.310 | 1,268 s | 0,824 s | **Modelo B** |

---

### Conclusão

Os experimentos evidenciam que **não existe modelo "melhor" em termos absolutos no Apache Cassandra**.
O desempenho de leitura é determinado pelo grau de alinhamento entre a *partition key* e o padrão de acesso da query:

- Perguntas que **agregam por estado em grandes janelas temporais** favorecem o **Modelo A** — uma única partição por estado cobre todo o histórico sem overhead de queries.
- Perguntas com **recorte temporal específico** (por mês ou faixa de meses) favorecem o **Modelo B** — a partição `(estado, ano_mes)` entrega exatamente os dados necessários, sem `ALLOW FILTERING`.
- O ponto de inflexão ocorre quando o número de partições do Modelo B cresce o suficiente para que o overhead de múltiplas queries supere o custo do scan com `ALLOW FILTERING` do Modelo A — como demonstrado no experimento com o intervalo 2005–2007 (~972 queries), onde o Modelo A foi ~7× mais rápido.

> Este comportamento é consistente com o princípio de *query-driven modeling* do Apache Cassandra: **modele os dados de acordo com as queries que serão executadas**.
