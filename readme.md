Aqui está o quadro consolidado dos três experimentos, focado apenas no que importa para o trabalho.

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
