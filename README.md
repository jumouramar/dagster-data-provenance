# Dagster Data Provenance

Proposta de modelo para captura e rastreamento de proveniência de dados em pipelines utilizando Dagster.

### Pré-requisitos

- Docker

### Como executar?

1. Após clonar o repositório, execute ```docker-compose up --build -d``` no terminal da pasta.
   
2. Acesse http://localhost:3000/


## Proveniência de Implantação

A cada execução do pipeline, uma linha é gravada na tabela `pipeline_provenance`:

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL | Chave primária |
| `run_id` | VARCHAR(255) | ID da run do Dagster |
| `environment_name` | VARCHAR(50) | Ambiente de execução |
| `python_version` | VARCHAR(100) | Versão completa do Python (`sys.version`) |
| `dependencies` | JSONB | Mapa `{ pacote: versão }` de todos os pacotes instalados |
| `git_hash` | VARCHAR(40) | Hash do commit (`git rev-parse HEAD`) |
| `recorded_at` | TIMESTAMPTZ | Timestamp da inserção (default `NOW()`) |

## Consultando a proveniência

(Opcional) Adicione a extensão `PostgresSQL`

