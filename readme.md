# PPCA_BDM

Projeto de estudo e experimentação com Apache Cassandra para análise da influência da modelagem de dados no desempenho, usando dados meteorológicos como base de teste.

## Objetivo

Este projeto tem como objetivo comparar duas abordagens de modelagem no Apache Cassandra, avaliando como a definição da chave primária e da chave de partição impacta operações de escrita e leitura.

A proposta é trabalhar com:

- um **modelo A**, propositalmente menos eficiente;
- um **modelo B**, otimizado para o padrão de consulta;
- scripts de carga e benchmark para medir diferenças de desempenho.

## Estrutura do projeto

```text
ppca_bdm/
├─ .venv/
├─ .gitignore
├─ docker-compose.yml
├─ requirements.txt
├─ README.md
├─ cql/
├─ scripts/
├─ data/
│  ├─ raw/
│  └─ processed/
└─ results/
   ├─ raw/
   └─ reports/
```

## Pré-requisitos

Antes de iniciar, é necessário ter instalado na máquina:

- [Git](https://git-scm.com/)
- [Python 3](https://www.python.org/)
- [VS Code](https://code.visualstudio.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Clonagem do repositório

Para continuar o projeto em outra máquina:

```powershell
cd C:\VSCode
git clone https://github.com/gustavo-plc/ppca_bdm.git
cd ppca_bdm
```

Depois, abra a pasta no VS Code.

## Criação do ambiente virtual Python

No terminal do VS Code, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Se o VS Code solicitar a criação de um ambiente isolado, e a `.venv` já tiver sido criada manualmente, basta selecionar o interpretador dessa mesma venv.

## Setup do Cassandra com Docker

Este projeto **não exige instalação nativa do Cassandra no Windows**.  
O banco será executado em um container Docker, o que facilita a reprodução do ambiente em qualquer máquina.

### Arquivo `docker-compose.yml`

O projeto utiliza um `docker-compose.yml` semelhante a este:

```yaml
services:
  cassandra:
    image: cassandra:latest
    container_name: cassandra-db
    ports:
      - "9042:9042"
    environment:
      CASSANDRA_CLUSTER_NAME: "tcc-cluster"
    volumes:
      - cassandra_data:/var/lib/cassandra

volumes:
  cassandra_data:
```

### Iniciar o Docker Desktop

Antes de subir o Cassandra, abra o **Docker Desktop** e aguarde até que ele esteja em execução.

É possível validar no terminal:

```powershell
docker --version
docker compose version
docker ps
```

Se `docker ps` funcionar sem erro, o daemon está pronto.

### Subir o container do Cassandra

Na raiz do projeto:

```powershell
docker compose up -d
```

Esse comando:

- baixa a imagem oficial do Cassandra, se necessário;
- cria o container `cassandra-db`;
- expõe a porta `9042`, usada pelo CQL;
- cria um volume persistente chamado `cassandra_data`.

### Verificar se o container está rodando

```powershell
docker ps
```

Você deve ver algo parecido com:

```text
CONTAINER ID   IMAGE              NAMES
xxxxxxxxxxxx   cassandra:latest   cassandra-db
```

### Acompanhar a inicialização

O Cassandra pode levar algum tempo até ficar pronto para conexões.

Para acompanhar os logs:

```powershell
docker logs -f cassandra-db
```

Se necessário, aguarde alguns instantes até o serviço estabilizar.

### Entrar no `cqlsh`

Quando o Cassandra estiver pronto, execute:

```powershell
docker exec -it cassandra-db cqlsh
```

Se tudo estiver correto, o prompt do Cassandra será aberto:

```text
Connected to tcc-cluster at 127.0.0.1:9042
[cqlsh ...]
cqlsh>
```

## Teste inicial no Cassandra

Uma vez dentro do `cqlsh`, é possível validar o ambiente com um teste simples.

### Criar o keyspace

```sql
CREATE KEYSPACE IF NOT EXISTS inmet
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
```

### Selecionar o keyspace

```sql
USE inmet;
```

### Criar uma tabela de teste

```sql
CREATE TABLE IF NOT EXISTS exemplo (
    id int PRIMARY KEY,
    nome text
);
```

### Inserir um registro

```sql
INSERT INTO exemplo (id, nome) VALUES (1, 'ok');
```

### Consultar o registro

```sql
SELECT * FROM exemplo;
```

Se o registro for retornado, o ambiente Cassandra está funcional.

## Encerrar ou reiniciar o ambiente

### Parar os containers

```powershell
docker compose down
```

### Subir novamente

```powershell
docker compose up -d
```

### Remover containers e volume persistente

Se quiser reiniciar completamente o banco local:

```powershell
docker compose down -v
```

> Atenção: esse comando remove também o volume `cassandra_data`, apagando os dados armazenados localmente.

## Próximos passos do projeto

Após validar o funcionamento do Cassandra, os próximos passos são:

1. criar os arquivos `.cql` do projeto;
2. definir o keyspace e as tabelas dos modelos A e B;
3. preparar os dados meteorológicos;
4. escrever scripts Python de carga;
5. executar benchmarks de escrita e leitura;
6. registrar os resultados em `results/`.

## Arquivos que devem ser versionados

Devem permanecer no GitHub:

- `docker-compose.yml`
- `requirements.txt`
- `README.md`
- arquivos `.cql`
- scripts Python
- resultados consolidados e relatórios

## Arquivos que não devem ser versionados

Não devem ser enviados ao GitHub:

- `.venv/`
- dados brutos muito grandes
- caches e arquivos temporários
- volumes internos do Docker

Esses itens são tratados no `.gitignore`.

## Fluxo básico de uso em outra máquina

Sempre que o projeto for aberto em outro computador, o fluxo recomendado é:

1. clonar o repositório;
2. criar e ativar a `.venv`;
3. instalar dependências com `requirements.txt`;
4. abrir o Docker Desktop;
5. subir o Cassandra com `docker compose up -d`;
6. acessar o banco com `docker exec -it cassandra-db cqlsh`.

## Observações

- O container do Cassandra é local à máquina onde o Docker está rodando.
- O GitHub **não armazena o container em si**, apenas os arquivos que descrevem sua configuração.
- O uso de Docker garante que o mesmo ambiente possa ser recriado facilmente em máquinas diferentes.