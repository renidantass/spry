from spry import ControllerBase, controller, delete, get, post, put

from taskboard.data import AppDbContext, CreateTodo, Todo


@controller(\"/todos\")
class TodosController(ControllerBase):
    def __init__(self, db: AppDbContext) -> None:
        self.db = db

    @get(\"/\")
    def list(self):
        return self.db.todos.all()

    @get(\"/{id}\")
    def get_by_id(self, id: int):
        todo = self.db.todos.find(id)
        return todo if todo is not None else self.not_found(\"Todo not found\")

    @post(\"/\")
    def create(self, todo: CreateTodo):
        entity = Todo(title=todo.title, done=False)
        self.db.todos.add(entity)
        self.db.save_changes()
        return self.created(f\"/todos/{entity.id}\", entity)

    @put(\"/{id}\")
    def update(self, id: int, todo: CreateTodo):
        entity = self.db.todos.find(id)
        if entity is None:
            return self.not_found(\"Todo not found\")
        entity.title = todo.title
        self.db.todos.update(entity)
        self.db.save_changes()
        return entity

    @delete(\"/{id}\")
    def remove(self, id: int):
        entity = self.db.todos.find(id)
        if entity is None:
            return self.not_found(\"Todo not found\")
        self.db.todos.remove(id)
        self.db.save_changes()
        return self.no_content()
