# Almoxarifado — Inventory API

Aplicação web e API REST para controle de almoxarifado, desenvolvida com **FastAPI**, **SQLAlchemy**, **Alembic**, **Jinja2** e PostgreSQL. O sistema permite organizar itens por categorias e subcategorias, controlar saldos, registrar entradas e saídas, importar itens por planilhas Excel e desfazer importações por lote.

A aplicação foi projetada para uso compartilhado por pessoas que recebem o endereço do sistema. O acesso geral é protegido por uma senha compartilhada, enquanto as operações de estoque ficam disponíveis dentro da área autenticada do almoxarifado.

## Funcionalidades principais

| Funcionalidade | Descrição |
| --- | --- |
| Categorias | Criação, edição e remoção de categorias principais. |
| Subcategorias | Organização hierárquica no formato categoria → subcategoria → item. |
| Navegação visual | Cartões responsivos e clicáveis para abrir diretamente uma categoria ou subcategoria. |
| Cadastro de itens | Criação de itens vinculados a uma categoria ou subcategoria. |
| Edição de itens | Alteração do nome, categoria, estoque mínimo e quantidade atual. |
| Entradas | Registro de recebimentos e acréscimos ao estoque. |
| Saídas | Registro de consumo ou retirada, impedindo saldo negativo. |
| Ajuste de quantidade | A edição direta da quantidade gera uma movimentação automática de ajuste quando o saldo muda. |
| Exclusão completa | Categorias e itens podem ser removidos mesmo com registros relacionados; os históricos dependentes são removidos junto. |
| Importação Excel | Importação de itens por arquivos `.xlsx` ou `.xlsm` dentro de uma categoria. |
| Histórico de importações | Exibição do nome, data e lote de cada importação na página da categoria. |
| Desfazer importação | Remoção de todos os itens e movimentações criados por um lote específico. |
| Estoque mínimo | Indicação visual de itens que precisam de reposição. |
| Acesso compartilhado | Proteção da área do almoxarifado por senha de uso geral. |
| Diagnóstico | Endpoint `/health` para verificar o estado da aplicação e do banco. |
| Documentação API | Swagger UI disponível em `/docs`. |

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| Python | Linguagem principal. |
| FastAPI | API REST, rotas web e validação de requisições. |
| SQLAlchemy | Modelos e acesso ao banco de dados. |
| Alembic | Controle versionado das alterações de banco. |
| PostgreSQL | Banco de produção no Supabase. |
| SQLite | Banco local para desenvolvimento. |
| Jinja2 | Renderização das páginas HTML. |
| openpyxl | Leitura e validação de planilhas Excel. |
| Uvicorn | Servidor ASGI local e de produção. |
| pytest | Testes automatizados. |
| TestClient/httpx | Testes das rotas HTTP. |

## Estrutura do projeto

```text
inventory_api/
├── app/
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   ├── static/
│   │   └── styles.css
│   └── templates/
│       ├── categories.html
│       ├── category_form.html
│       ├── category_import.html
│       ├── category_products.html
│       ├── product_edit_form.html
│       └── warehouse.html
├── migrations/
│   ├── env.py
│   └── versions/
├── tests/
│   └── test_api.py
├── alembic.ini
├── Procfile
├── requirements.txt
└── README.md
```

O arquivo local `inventory.db` é criado para desenvolvimento e não deve ser versionado. Backups locais também permanecem fora do repositório.

## Modelo de dados

| Entidade | Campos principais | Responsabilidade |
| --- | --- | --- |
| `Category` | `id`, `name`, `parent_id` | Representa categoria principal ou subcategoria. |
| `Product` | `id`, `name`, `quantity`, `category_id`, `minimum_quantity`, `import_batch_id` | Representa o item e seu saldo atual. |
| `StockMovement` | `id`, `product_id`, `movement_type`, `quantity`, `created_at` | Registra entradas, saídas e ajustes de quantidade. |
| `ImportBatch` | `id`, `category_id`, `filename`, `created_at` | Identifica uma importação Excel e permite desfazê-la. |

A coluna `Category.parent_id` permite relacionar uma subcategoria à categoria principal. A coluna `Product.import_batch_id` liga os itens importados ao lote responsável pela criação.

## Regras de negócio

A quantidade de um produto nunca pode ficar negativa. Uma saída superior ao saldo disponível é rejeitada sem alterar o produto e sem criar movimentação. Cada entrada ou saída aceita gera um registro em `stock_movements`.

A edição direta da quantidade preserva o histórico: quando o novo valor é diferente do anterior, o sistema cria uma movimentação do tipo `adjustment` com a diferença correspondente.

A remoção de um item apaga também suas movimentações relacionadas. A remoção de uma categoria remove os itens vinculados e os históricos dependentes, permitindo excluir uma categoria mesmo quando ela já possui movimentações.

Uma importação Excel cria um `ImportBatch`. O botão **Desfazer importação** usa esse lote para remover os produtos importados e as movimentações iniciais relacionadas, sem afetar produtos de outros lotes.

## Formato da planilha Excel

A importação aceita arquivos `.xlsx` e `.xlsm`. A planilha deve conter uma linha de cabeçalho e colunas compatíveis com os campos do item. Recomenda-se usar os seguintes nomes:

| Coluna | Obrigatória | Descrição |
| --- | --- | --- |
| `name` ou `nome` | Sim | Nome do item. |
| `quantity` ou `quantidade` | Não | Quantidade inicial; quando omitida, utiliza zero conforme a validação da aplicação. |
| `minimum_quantity` ou `estoque_minimo` | Não | Limite para alerta de reposição. |

A importação é feita a partir da página da categoria ou subcategoria, pelo botão **Importar Excel**. Após a conclusão, o lote aparece no histórico da mesma página.

## Execução local

### Pré-requisitos

É necessário ter Python instalado, Git e as dependências listadas em `requirements.txt`.

### Criar o ambiente virtual

No macOS ou Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Instalar dependências

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Configuração local

O projeto utiliza SQLite localmente por padrão quando não há uma URL de PostgreSQL configurada. Variáveis sensíveis devem ser definidas no ambiente ou em um arquivo `.env` ignorado pelo Git. Nunca publique senhas, tokens ou URLs de conexão com credenciais.

Quando necessário, defina a conexão de banco para uma sessão do Terminal:

```bash
export DATABASE_URL='sua_url_de_conexao'
```

A senha compartilhada e o segredo de sessão devem ser configurados conforme os nomes utilizados em `app/security.py` e mantidos fora do repositório.

### Executar a aplicação

```bash
uvicorn app.main:app --reload
```

A aplicação local ficará disponível em:

| Endereço | Uso |
| --- | --- |
| `http://127.0.0.1:8000` | Página principal e acesso ao sistema. |
| `http://127.0.0.1:8000/health` | Diagnóstico da aplicação e do banco. |
| `http://127.0.0.1:8000/docs` | Documentação interativa da API. |
| `http://127.0.0.1:8000/openapi.json` | Especificação OpenAPI. |

## Migrações do banco

O banco local e o banco de produção devem ser atualizados por Alembic. Verifique a revisão atual com:

```bash
alembic current
```

Aplique todas as migrações pendentes com:

```bash
alembic upgrade head
```

A revisão atual do projeto inclui, entre outras, as alterações de `parent_id` em `categories` e `import_batch_id` em `products`, além da criação de `import_batches`.

Não use `alembic stamp head` para substituir uma migração que ainda não foi executada. Em caso de erro, preserve a mensagem completa, verifique o estado do banco e corrija a migração antes de tentar novamente.

## Testes

Os testes utilizam um banco SQLite temporário em memória e não alteram o arquivo local `inventory.db`. Execute-os com o Python do ambiente virtual:

```bash
python -m pytest -q
```

A suíte validada atualmente contém 13 testes, incluindo:

| Grupo | Validação |
| --- | --- |
| Categorias e produtos | Criação, listagem e atualização. |
| Movimentações | Entrada, saída válida e bloqueio de estoque negativo. |
| Exclusão | Exclusão de item sem movimentação e com histórico relacionado. |
| Reorganização | Transferência de item entre categorias pela interface web. |
| Autenticação | Redirecionamento e acesso à área protegida. |
| Diagnóstico | Resposta do endpoint `/health`. |

Também é recomendável executar:

```bash
python -m compileall -q app migrations

git diff --check
```

## Deploy com Supabase e Render

O Supabase fornece o banco PostgreSQL de produção. O Render hospeda a aplicação FastAPI.

O fluxo recomendado é:

1. Executar os testes localmente.
2. Conferir `git diff --check` e `git status --short`.
3. Criar um commit somente com os arquivos necessários.
4. Enviar o commit para a branch acompanhada pelo Render, normalmente `main`.
5. Aplicar `alembic upgrade head` usando a conexão PostgreSQL do Supabase.
6. Conferir no Supabase as tabelas e colunas esperadas.
7. Aguardar ou iniciar o deploy no Render.
8. Abrir a URL pública e verificar login, categorias, itens, movimentações e importação Excel.

No Render, configure as variáveis de ambiente necessárias no painel do serviço. A senha compartilhada, o segredo de sessão e `DATABASE_URL` devem ser cadastrados como variáveis protegidas e nunca no código ou no README.

Depois do deploy, verifique:

```text
https://SEU-ENDERECO.onrender.com/health
```

Também teste a página inicial, o acesso à área do almoxarifado e uma categoria com itens. Não utilize dados reais para testes destrutivos em produção; para testar desfazer importação ou exclusão, use um lote e itens de teste identificados.

## Checklist operacional

| Item | Conferência |
| --- | --- |
| Banco | `alembic current` mostra a revisão mais recente. |
| Aplicação | `/health` retorna estado saudável. |
| Acesso | A senha compartilhada permite entrar na área protegida. |
| Categorias | Cards são clicáveis e categorias vazias oferecem ações. |
| Subcategorias | A subcategoria permanece vinculada à categoria principal. |
| Itens | É possível criar, editar, mover e remover itens. |
| Estoque | Saídas acima do saldo são recusadas. |
| Histórico | Entradas, saídas e ajustes aparecem associados ao item. |
| Excel | `.xlsx` e `.xlsm` válidos são importados. |
| Desfazer | O histórico mostra o lote e remove somente seus itens quando solicitado. |
| Segurança | Segredos, senhas e bancos locais não estão no Git. |

## Referências

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [openpyxl Documentation](https://openpyxl.readthedocs.io/)
- [Supabase — Connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Render Documentation](https://render.com/docs)
