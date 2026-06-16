from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Section:
    title: str
    body: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    code: str | None = None
    code_language: str | None = None
    note: str | None = None
    visual: str | None = None


@dataclass(slots=True)
class Page:
    slug: str
    title: str
    eyebrow: str
    summary: str
    highlights: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)


PAGES: list[Page] = [
    Page(
        slug="getting-started",
        title="Getting Started",
        eyebrow="Quick Start",
        summary="Instale o framework, gere um projeto, rode localmente e entenda o caminho feliz sem tropecar no setup.",
        highlights=[
            "`AppBuilder` centraliza bootstrap, DI e rotas.",
            "Controllers sao descobertos automaticamente no pacote da aplicacao.",
            "`DbContext` e `DbSet` cobrem o CRUD inicial sem depender de uma stack pesada.",
        ],
        sections=[
            Section(
                title="Instalacao",
                body=[
                    "O melhor fluxo para desenvolvimento local e instalar o `Spry` em modo editavel com `pip install -e .`.",
                    "Depois disso, a CLI `spry` fica disponivel e todas as alteracoes locais no framework passam a refletir imediatamente no ambiente.",
                ],
                code_language="bash",
                code='pip install -e .\npython -m spry.cli new taskboard',
            ),
            Section(
                title="Primeiro ciclo local",
                body=[
                    "Se voce estiver avaliando o framework, a maneira mais rapida de gerar confianca e seguir o ciclo completo: scaffold, run, migrate, seed e hot reload.",
                    "Esse e o caminho que cobre quase tudo que um developer vai fazer na primeira hora com o projeto.",
                ],
                bullets=[
                    "`spry new taskboard` para gerar o projeto base.",
                    "`spry run --app taskboard.app:create_app` para subir o app.",
                    "`spry migrate add initial --context taskboard.data:AppDbContext` para gerar schema SQL.",
                    "`spry seed --entry taskboard.seed:seed --context taskboard.data:AppDbContext --database taskboard.db` para popular dados.",
                ],
            ),
            Section(
                title="Seu primeiro app",
                body=[
                    "O exemplo abaixo mostra o nucleo do framework: uma entidade, um `DbContext`, um controller e o bootstrap final.",
                    "Repare que o controller nao precisa ser registrado manualmente. O `AppBuilder` faz descoberta automatica no pacote da aplicacao durante o `build()`.",
                ],
                visual="todo-flow",
                code_language="python",
                code='from dataclasses import dataclass\n\nfrom spry import AppBuilder, ControllerBase, DbContext, controller, dbset, get, key, post\n\n\n@dataclass(slots=True)\nclass Todo:\n    id: int | None = key()\n    title: str = ""\n    done: bool = False\n\n\nclass AppDbContext(DbContext):\n    todos = dbset(Todo)\n\n\n@controller("/todos")\nclass TodosController(ControllerBase):\n    def __init__(self, db: AppDbContext) -> None:\n        self.db = db\n\n    @get("/")\n    def list(self):\n        return self.db.todos.all()\n\n    @post("/")\n    def create(self, todo: Todo):\n        self.db.todos.add(todo)\n        self.db.save()\n        return self.created(f"/todos/{todo.id}", todo)\n\n\nbuilder = AppBuilder()\nbuilder.add_db_context(AppDbContext)\napp = builder.build()\napp.run()',
            ),
            Section(
                title="Estrutura recomendada",
                body=[
                    "O template padrao organiza a aplicacao em um pacote `src/<app>`, um `main.py` na raiz e um `appsettings.json` com as configuracoes basicas.",
                    "Isso ajuda tanto o import local quanto a descoberta automatica de controllers e outros componentes do app.",
                ],
                bullets=[
                    "`app.py`: compoe o `AppBuilder` e retorna o `Application`.",
                    "`controllers.py`: endpoints HTTP por bounded context pequeno.",
                    "`data.py`: entidades e `DbContext`.",
                    "`seed.py`: dados iniciais e setup local.",
                ],
            ),
            Section(
                title="Quando algo der errado",
                body=[
                    "As falhas mais comuns no onboarding sao import path, nome errado em `--app` e mismatch entre DTO e payload.",
                ],
                bullets=[
                    "Se falhar import, cheque `taskboard.app:create_app` e o `src/` do projeto.",
                    "Se a rota responder `404`, cheque se a classe tem `@controller` e o metodo tem decorator HTTP.",
                    "Se o payload responder `422`, compare o JSON com a `dataclass` de entrada.",
                ],
            ),
        ],
    ),
    Page(
        slug="api-development",
        title="API Development",
        eyebrow="HTTP Layer",
        summary="Guia pratico para construir APIs no Spry com controllers, middleware, binding e respostas reutilizaveis.",
        highlights=[
            "`ControllerBase` reduz duplicacao de respostas HTTP comuns.",
            "Rotas com parametros como `/todos/{id}` continuam simples e tipadas.",
            "Binding automatico de query string, route params, payload JSON e servicos DI.",
        ],
        sections=[
            Section(
                title="Controllers",
                body=[
                    "Controllers sao classes decoradas com `@controller`, resolvidas pelo container a cada request.",
                    "Cada metodo pode receber parametros vindos da rota, query string, payload JSON ou servicos registrados no escopo.",
                    "No fluxo normal, voce so cria a classe dentro do pacote da aplicacao e deixa a descoberta automatica fazer o resto.",
                ],
                visual="routing-flow",
                code_language="python",
                code='@controller("/todos")\nclass TodosController(ControllerBase):\n    def __init__(self, db: AppDbContext) -> None:\n        self.db = db\n\n    @get("/{id}")\n    def get_by_id(self, id: int):\n        todo = self.db.todos.find(id)\n        return todo if todo is not None else self.not_found("Todo nao encontrado")',
            ),
            Section(
                title="ControllerBase",
                body=[
                    "Para API, `ControllerBase` e o ponto de partida recomendado. Ele encapsula respostas comuns e evita repetir `Response.json(...)` ou `Response.empty(...)` o tempo todo.",
                ],
                bullets=[
                    "`self.ok(...)`",
                    "`self.created(location, value)`",
                    "`self.bad_request(...)`",
                    "`self.not_found(...)`",
                    "`self.no_content()`",
                ],
                code_language="python",
                code='@post("/")\ndef create(self, todo: CreateTodo):\n    entity = Todo(title=todo.title)\n    self.db.todos.add(entity)\n    self.db.save()\n    return self.created(f"/todos/{entity.id}", entity)',
            ),
            Section(
                title="Handlers avulsos",
                body=[
                    "Quando voce nao precisa de uma classe inteira, `map_get`, `map_post`, `map_put`, `map_delete` e `map_patch` cobrem handlers pequenos.",
                ],
                code_language="python",
                code='builder.map_get("/health", lambda: {"status": "ok"})',
            ),
            Section(
                title="Middleware",
                body=[
                    "Middleware recebe `HttpContext` e `next_handler`, podendo observar request, enriquecer response ou interromper o fluxo.",
                    "Isso e util para logging, cabecalhos, autenticacao e politicas transversais do app.",
                ],
                code_language="python",
                code='def server_header(context, next_handler):\n    response = next_handler()\n    response.headers.setdefault("X-Powered-By", "Spry")\n    return response\n\n\nbuilder.use(server_header)',
            ),
            Section(
                title="Validacao",
                body=[
                    "Payloads mapeados para `dataclasses` sao validados no binding. Campos obrigatorios ausentes ou tipos invalidos retornam `422` com detalhes por campo.",
                    "Na pratica, isso significa que voce deve separar DTOs de entrada da entidade persistida sempre que o contrato HTTP nao for identico ao modelo do banco.",
                ],
                note='Use `dataclasses` pequenas e especificas para input. Evite reutilizar a entidade inteira como DTO de entrada quando o contrato HTTP for diferente.',
            ),
        ],
    ),
    Page(
        slug="mvc-development",
        title="MVC Development",
        eyebrow="Server-Side HTML",
        summary="Como construir apps MVC no Spry com `Controller`, layouts, partials e views em arquivo, sem HTML gigante dentro do Python.",
        highlights=[
            "`Controller` adiciona `view()`, `partial_view()` e `redirect()`.",
            "Views ficam em arquivos dentro de `views/`.",
            "O fluxo final fica mais proximo de um `cshtml` do que de f-strings enormes em Python.",
        ],
        sections=[
            Section(
                title="Base MVC",
                body=[
                    "Para MVC, a classe recomendada e `Controller`. Ela herda de `ControllerBase` e adiciona helpers de view e redirect.",
                    "Com isso, o controller fica responsavel por coordenar dados e escolher a view, nao por construir HTML bruto.",
                ],
                code_language="python",
                code='class HomeController(Controller):\n    def __init__(self, db: AppDbContext, view_renderer: ViewRenderer) -> None:\n        super().__init__(view_renderer)\n        self.db = db\n\n    @get("/")\n    def index(self):\n        return self.view("home/index", {"page_title": "Dashboard"})',
            ),
            Section(
                title="Registrando views",
                body=[
                    "O bootstrap MVC deve registrar o renderer com `builder.add_views(...)`.",
                    "Depois disso, `Controller` pode resolver layout, pagina e partials automaticamente a partir da pasta `views/`.",
                ],
                code_language="python",
                code='builder = AppBuilder(base_path=BASE_DIR)\nbuilder.add_views(root_path=BASE_DIR)\nbuilder.add_db_context(AppDbContext)\napp = builder.build()',
            ),
            Section(
                title="Estrutura recomendada",
                body=[
                    "A organizacao recomendada para MVC tenta separar responsabilidades da mesma forma que um developer espera em stacks server-side maduras.",
                ],
                bullets=[
                    "`views/shared/_layout.html`: layout principal.",
                    "`views/home/index.html`: pagina principal.",
                    "`views/home/_todo_card.html`: partial reutilizavel.",
                    "`static/site.css`: visual do app.",
                ],
            ),
            Section(
                title="Quando usar partials",
                body=[
                    "Sempre que um bloco de UI se repetir, mova para partial. Isso reduz ruido no controller e deixa a view principal mais legivel.",
                    "A regra pratica e simples: se uma secao ja parece um componente visual, ela provavelmente merece um arquivo proprio.",
                ],
                note="Se o controller estiver montando strings HTML demais, a view esta abstraindo pouco. Empurre esse markup para partials ou para a view principal.",
            ),
        ],
    ),
    Page(
        slug="orm-and-data",
        title="ORM And Data",
        eyebrow="Persistence",
        summary="O ORM do Spry cobre o caminho feliz de CRUD, relacoes basicas e migracoes SQL para SQLite, com foco em clareza operacional.",
        highlights=[
            "`DbContext` gerencia conexao, schema e transacao.",
            "`DbSet` expõe `all`, `first`, `where`, `find`, `add`, `update`, `remove` e `include`.",
            "`foreign_key`, `navigation` e `navigation_many` ajudam a modelar relacoes sem ficar verboso.",
        ],
        sections=[
            Section(
                title="Modelando entidades",
                body=[
                    "Entidades sao `dataclasses`. Campos com `key()` viram primary key, e `foreign_key()` gera a constraint no schema SQL.",
                    "A recomendacao pratica e manter as entidades pequenas, com defaults previsiveis e pouca logica embutida.",
                ],
                visual="orm-relations",
                code_language="python",
                code='@dataclass(slots=True)\nclass Author:\n    id: int | None = key()\n    name: str = ""\n    posts: list["Post"] = navigation_many(lambda: Post, foreign_key="author_id")\n\n\n@dataclass(slots=True)\nclass Post:\n    author_id: int = foreign_key(Author)\n    id: int | None = key()\n    title: str = ""\n    author: Author | None = navigation(Author, foreign_key="author_id")',
            ),
            Section(
                title="Consultas e includes",
                body=[
                    "A API e deliberadamente pequena. A ideia e privilegiar clareza sobre uma DSL extensa.",
                    "Relacoes sao carregadas sob demanda com `include`.",
                ],
                code_language="python",
                code='post = db.posts.first(title="Hello")\ndb.posts.include(post, "author")\n\nauthor = db.authors.first(name="Ada")\ndb.authors.include(author, "posts")',
            ),
            Section(
                title="Schema e transacao",
                body=[
                    "Durante o bootstrap local, `ensure_created()` e suficiente para levantar o banco rapidamente.",
                    "Em fluxos controlados, prefira migracoes SQL versionadas e `transaction()` para unidades de trabalho maiores.",
                ],
                code_language="python",
                code='with db.transaction():\n    db.todos.add(Todo(title="Ship v0.2"))\n    db.todos.add(Todo(title="Write docs"))',
            ),
            Section(
                title="Praticas recomendadas",
                bullets=[
                    "Use `CreateSomething` e `UpdateSomething` como DTOs de entrada quando a entidade nao bate com o payload.",
                    "Deixe `DbContext` pequeno e coeso por bounded context.",
                    "Prefira migracoes SQL versionadas para ambientes compartilhados.",
                    "Use `include(...)` explicitamente quando precisar de relacoes carregadas.",
                ],
            ),
        ],
    ),
    Page(
        slug="tooling-and-cli",
        title="Tooling And CLI",
        eyebrow="Developer Experience",
        summary="A CLI foi desenhada para cobrir o ciclo diario de um developer: scaffold, run, watch, migrate e seed sem atrito desnecessario.",
        highlights=[
            "`spry new` gera a estrutura base do projeto.",
            "`spry run` e `spry watch` agilizam o loop local.",
            "`spry migrate` e `spry seed` ajudam no setup do banco.",
        ],
        sections=[
            Section(
                title="Gerando projeto",
                body=[
                    "Os templates atuais priorizam o primeiro commit produtivo: `app.py`, `DbContext`, seed, configuracao e uma primeira tela ou API funcional.",
                ],
                code_language="bash",
                code='spry new inventory_api\nspry new backoffice --template mvc',
            ),
            Section(
                title="Rodando e observando alteracoes",
                body=[
                    "`run` resolve uma factory no formato `module:callable`. `watch` reinicia o processo quando arquivos Python ou `appsettings.json` mudam.",
                    "Se o app e o framework estiverem lado a lado em um workspace, a CLI tenta inferir os paths de import do projeto automaticamente.",
                ],
                visual="cli-loop",
                code_language="bash",
                code='spry run --app inventory_api.app:create_app\nspry watch --app inventory_api.app:create_app --path .',
            ),
            Section(
                title="Migracoes e seed",
                body=[
                    "As migracoes geram SQL a partir do schema do `DbContext`. O comando de seed executa um entrypoint Python e pode receber um contexto de banco.",
                ],
                code_language="bash",
                code='spry migrate add initial --context inventory_api.data:AppDbContext\nspry migrate apply --database inventory.db\nspry seed --entry inventory_api.seed:seed --context inventory_api.data:AppDbContext --database inventory.db',
            ),
            Section(
                title="Comandos que voce mais vai usar",
                bullets=[
                    "`spry new <nome>` para comecar rapido.",
                    "`spry run --app modulo.app:create_app` para subir o app.",
                    "`spry watch --app modulo.app:create_app` para loop de desenvolvimento.",
                    "`spry migrate add ...` e `spry migrate apply ...` para schema.",
                    "`spry seed ...` para bootstrap de dados locais.",
                ],
            ),
        ],
    ),
    Page(
        slug="troubleshooting",
        title="Troubleshooting",
        eyebrow="Debugging Guide",
        summary="Os erros mais comuns ao instalar, rodar ou evoluir um app Spry e como resolver rapido sem ficar adivinhando.",
        highlights=[
            "Import path e naming errado sao as falhas mais comuns no onboarding.",
            "`404` quase sempre significa rota/controller fora da convencao esperada.",
            "`422` normalmente e mismatch entre payload e DTO de entrada.",
        ],
        sections=[
            Section(
                title="ModuleNotFoundError",
                body=[
                    "Quando o Python nao encontra `my_app.app` ou algo parecido, o problema quase sempre e caminho de import.",
                    "Confirme se voce esta dentro da pasta do projeto ou se o `PYTHONPATH` inclui o `src/` correto.",
                ],
                code_language="bash",
                code='spry run --app taskboard.app:create_app\n\n# PowerShell\n$env:PYTHONPATH="C:\\caminho\\spry\\src;C:\\caminho\\taskboard\\src"\npython -m spry.cli run --app taskboard.app:create_app',
            ),
            Section(
                title="404 em rota existente",
                bullets=[
                    'Cheque `@controller("/prefix")` na classe.',
                    "Cheque o decorator HTTP no metodo (`@get`, `@post`, etc.).",
                    "Cheque o path final: prefixo + rota do metodo.",
                    "Cheque se o controller esta dentro do pacote da aplicacao para a descoberta automatica funcionar.",
                ],
            ),
            Section(
                title="422 de validacao",
                body=[
                    "`422` significa que o binding do payload falhou. Em geral, a aplicacao estava esperando uma `dataclass` e o JSON nao bateu com ela.",
                ],
                bullets=[
                    "campo obrigatorio ausente",
                    "tipo diferente do esperado",
                    "nome de propriedade divergente",
                    "uso da entidade persistida como DTO quando o contrato HTTP e outro",
                ],
            ),
            Section(
                title="MVC nao encontra view",
                body=[
                    "Se `self.view(...)` quebrar, o problema normalmente esta no caminho da view ou na falta de `builder.add_views(...)` no bootstrap.",
                ],
                code_language="python",
                code='builder = AppBuilder(base_path=BASE_DIR)\nbuilder.add_views(root_path=BASE_DIR)\n\nreturn self.view("home/index", {"page_title": "Home"})',
            ),
        ],
    ),
    Page(
        slug="architecture",
        title="Architecture",
        eyebrow="How Spry Fits Together",
        summary="Spry tem poucas pecas e cada uma tenta fazer uma coisa so, mantendo o caminho feliz direto de entender e debugar.",
        highlights=[
            "Configuracao e DI vivem no `AppBuilder`.",
            "`Application` executa o pipeline, resolve rotas e expõe WSGI/ASGI.",
            "O ORM descobre metadados a partir das `dataclasses` registradas no `DbContext`.",
        ],
        sections=[
            Section(
                title="Bootstrap",
                body=[
                    "`AppBuilder` carrega configuracao, registra servicos e agrega rotas. Ao chamar `build()`, voce recebe um `Application` pronto para WSGI ou ASGI.",
                    "Nesse momento tambem acontece a descoberta automatica de controllers do pacote da aplicacao.",
                ],
                visual="architecture-map",
            ),
            Section(
                title="Pipeline por request",
                body=[
                    "Cada request cria um escopo DI. O pipeline passa pelos middlewares, resolve a rota e invoca o handler final com binding de parametros.",
                    "Servicos `scoped`, como `DbContext`, vivem exatamente por request, o que simplifica o lifecycle da persistencia.",
                ],
            ),
            Section(
                title="Bases de controller",
                body=[
                    "`ControllerBase` existe para API. `Controller` existe para MVC e herda a base comum. Essa separacao mantem reuso sem empurrar responsabilidades HTML para quem so precisa de JSON.",
                ],
            ),
            Section(
                title="Trade-offs intencionais",
                bullets=[
                    "Sem metaprogramacao excessiva: menos magia, mais leitura direta do codigo.",
                    "SQLite como alvo inicial do ORM: escopo pequeno e previsivel para v0.x.",
                    "Migracoes SQL simples: melhor clareza agora do que um sistema incompleto de diffs automaticos.",
                ],
                note='A proposta do Spry nao e competir em superficie com Django ou FastAPI hoje. A proposta e entregar um caminho opinado, coeso e extensivel.',
            ),
        ],
    ),
]


PAGE_MAP = {page.slug: page for page in PAGES}
