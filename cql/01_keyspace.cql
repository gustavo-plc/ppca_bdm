-- Keyspace do projeto
-- SimpleStrategy é adequado para ambiente local de desenvolvimento (single node)
CREATE KEYSPACE IF NOT EXISTS inmet
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};