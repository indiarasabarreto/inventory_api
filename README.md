# Inventory API

API REST desenvolvida com **FastAPI** para controle de categorias, produtos e movimentações de estoque. O projeto mantém um saldo atual por produto e preserva o histórico de entradas e saídas, impedindo que uma operação gere estoque negativo.

> Esta primeira versão foi construída como projeto de portfólio e também estabelece uma base técnica para uma futura solução de controle de almoxarifado.

## Funcionalidades

| Funcionalidade | Descrição |
| --- | --- |
| Verificação de saúde | Informa se a API está disponível. |
| Categorias | Cria e lista categorias com nomes únicos. |
| Produtos | Cria e lista produtos vinculados a uma categoria. |
| Estoque inicial | Armazena a quantidade inicial de cada produto. |
| Movimentações | Registra entradas e saídas de estoque. |
| Regra de saldo | Impede saídas superiores à quantidade disponível. |
| Histórico | Lista as movimentações de cada produto da mais recente para a mais antiga. |
| Documentação interativa | Expõe os endpoints em `/docs` com Swagger UI. |
| Testes | Valida cadastro, movimentação válida e bloqueio de saldo negativo. |

## Tecnologias

| Tecnologia | Uso no projeto |
| --- | --- |
| Python | Linguagem principal. |
| FastAPI | Criação dos endpoints REST e documentação OpenAPI. |
| Uvicorn | Servidor ASGI usado no desenvolvimento. |
| SQLAlchemy | Modelagem e acesso ao banco de dados. |
| SQLite | Banco local da versão inicial. |
| Pydantic | Validação de JSON de entrada e respostas tipadas. |
| pytest | Testes automatizados. |
| httpx / TestClient | Cliente HTTP usado pelos testes. |

## Estrutura do projeto

```
inventory-api/
├── app/
│   ├── __init__.py
│   ├── database.py          # Engine, sessão e dependência de banco
│   ├── main.py              # Aplicação FastAPI e endpoints
│   ├── models.py            # Tabelas SQLAlchemy
│   └── schemas.py           # Schemas Pydantic de entrada e resposta
├── tests/
│   └── test_api.py          # Testes automatizados
├── .gitignore
├── inventory.db             # Criado localmente; não deve ser versionado
└── requirements.txt
```

## Modelo de dados

| Entidade | Campos principais | Responsabilidade |
| --- | --- | --- |
| `Category` | `id`, `name` | Agrupa produtos, como Eletrônicos ou Limpeza. |
| `Product` | `id`, `name`, `sku`, `unit_price`, `quantity`, `category_id` | Representa o item controlado em estoque. |
| `StockMovement` | `id`, `product_id`, `movement_type`, `quantity`, `created_at` | Registra cada entrada (`in` ) ou saída (`out`). |

Cada produto pertence a uma categoria. Cada movimentação pertence a um produto. O saldo atual é armazenado em `Product.quantity`, enquanto a tabela de movimentações preserva a rastreabilidade de cada alteração.

## Regras de negócio

| Regra | Comportamento |
| --- | --- |
| Categoria única | Não permite repetir o mesmo nome. |
| SKU único | Não permite repetir a identificação de um produto. |
| Preço positivo | O valor unitário deve ser maior que zero. |
| Estoque inicial válido | A quantidade inicial não pode ser negativa. |
| Tipo de movimento | Aceita somente `in` ou `out`. |
| Saída protegida | Recusa a operação se a saída for maior que o saldo atual. |
| Histórico preservado | Cada alteração aceita cria um registro de movimentação. |

## Como executar localmente

### Pré-requisitos

É necessário ter **Python 3.12 ou superior** instalado. A aplicação foi desenvolvida com ambiente virtual Python.

### 1. Criar e ativar o ambiente virtual

No macOS ou Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### 3. Iniciar a API

```bash
uvicorn app.main:app --reload
```

A API ficará disponível em [http://127.0.0.1:8000](http://127.0.0.1:8000).

| URL | Uso |
| --- | --- |
| [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Verifica se a API está disponível. |
| [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Abre a documentação interativa. |
| [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) | Retorna a especificação OpenAPI em JSON. |

## Endpoints

| Método | Rota | Finalidade |
| --- | --- | --- |
| `GET` | `/health` | Retorna o estado da API. |
| `POST` | `/categories` | Cria uma categoria. |
| `GET` | `/categories` | Lista categorias. |
| `POST` | `/products` | Cria um produto. |
| `GET` | `/products` | Lista produtos; aceita filtro opcional por `category_id`. |
| `POST` | `/stock-movements` | Registra entrada ou saída. |
| `GET` | `/products/{product_id}/movements` | Lista o histórico de um produto. |

## Exemplos de uso

### Criar categoria

```json
POST /categories

{
  "name": "Eletrônicos"
}
```

### Criar produto

```json
POST /products

{
  "name": "Teclado mecânico",
  "sku": "TEC-MEC-001",
  "unit_price": 299.90,
  "quantity": 10,
  "category_id": 1
}
```

### Registrar entrada

```json
POST /stock-movements

{
  "product_id": 1,
  "movement_type": "in",
  "quantity": 5
}
```

### Registrar saída

```json
POST /stock-movements

{
  "product_id": 1,
  "movement_type": "out",
  "quantity": 3
}
```

Uma tentativa de saída acima do saldo disponível retorna `422 Unprocessable Entity` e não altera o produto nem cria histórico.

> O campo `unit_price` pode aparecer entre aspas na resposta JSON. O projeto usa `Decimal` para preservar a precisão de valores monetários, evitando imprecisões de ponto flutuante.

## Testes

Os testes utilizam um banco SQLite temporário em memória e não modificam o arquivo local `inventory.db`.

```bash
python3 -m pytest -q
```

| Teste | Validação |
| --- | --- |
| Criação de categoria e produto | Confirma persistência e listagem dos dados. |
| Movimentação válida | Confirma atualização de saldo e registro do histórico. |
| Estoque negativo | Confirma retorno `422`, saldo inalterado e ausência de evento. |

## Evolução para um almoxarifado

A API já possui a base essencial de um almoxarifado: itens, categorias, saldo, entradas, saídas e rastreabilidade. Para atender uma operação real, as melhorias devem ser introduzidas em etapas pequenas, priorizando os controles usados diariamente.

| Prioridade | Evolução | Benefício operacional |
| --- | --- | --- |
| Alta | Unidade de medida, como unidade, pacote, quilo ou litro | Evita saídas ambíguas e melhora a contagem. |
| Alta | Estoque mínimo por produto | Permite identificar itens que precisam de reposição. |
| Alta | Motivo e responsável pela movimentação | Registra contexto, como consumo, doação, compra ou perda. |
| Média | Localização física | Informa sala, armário, prateleira ou depósito do item. |
| Média | Fornecedores e compras | Registra origem, custo e reposição. |
| Média | Relatórios de consumo | Ajuda a entender frequência de uso e necessidade de compra. |
| Avançada | Usuários e permissões | Separa consulta, registro e administração. |
| Avançada | Interface web | Facilita o uso por pessoas que não utilizam a documentação da API. |

Antes de usar o sistema no dia a dia, é recomendável levantar as rotinas do almoxarifado, decidir quem poderá registrar movimentações e definir quais dados precisam ficar restritos. Dados de pessoas devem ser limitados ao mínimo necessário para a operação.

## Próximos passos técnicos

Após estabilizar o modelo, substitua `Base.metadata.create_all(...)` por migrações com Alembic e considere PostgreSQL para uma implantação multiusuário. Também adicione testes para cada nova regra antes de confiar nela em uma operação real.

## Referências

- [FastAPI Documentation](https://fastapi.tiangolo.com/)

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

- [Pydantic Documentation](https://docs.pydantic.dev/)

- [pytest Documentation](https://docs.pytest.org/)