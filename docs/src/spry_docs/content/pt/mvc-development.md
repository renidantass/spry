---
title: Desenvolvimento MVC
order: 3
description: Views, layouts, partials e HTML server-side
tags: mvc, views, templates, html
---

## Controller MVC

Use `Controller` em vez de `ControllerBase` para apps que servem HTML:

```python
from spry.controllers import Controller
from spry.routing import controller, get

@controller("/")
class HomeController(Controller):
    def __init__(self, view_renderer):
        super().__init__(view_renderer)

    @get("/")
    def index(self):
        return self.view("home/index", {"title": "Home"})
```

## Views e Layouts

```
views/
  shared/
    _layout.html      → Layout principal com {{ body }}
  home/
    index.html        → View renderizada dentro do layout
    _card.html        → Partial (prefixo _)
```

### Layout

```html
<!DOCTYPE html>
<html>
<head><title>{{ page_title }}</title></head>
<body>
  {{ body }}
</body>
</html>
```

### View

```html
<h1>{{ title }}</h1>
<p>{{ description }}</p>
```

## Template Engine

O Spry vem com duas engines:

```python
# Engine padrão (zero dependências)
builder.add_views(engine="spry")

# Jinja2 (pip install spry-core[jinja2])
builder.add_views(engine="jinja2")
```

### Sintaxe da engine Spry

```
{{ var }}              → Interpolação com escape
{{ var|upper }}        → Filters: upper, lower, default, safe
{% if cond %}...{% endif %}
{% for item in items %}...{% endfor %}
{% include "partial" %}
{% include "partial" without context %}
{# comment #}
```

### Partials

Renderize pedaços de HTML no controller:

```python
todo_cards = HtmlString("".join(
    str(self.partial_view("home/_card", {"title": todo.title}))
    for todo in todos
))
return self.view("home/index", {"cards": todo_cards})
```

## i18n em Templates

```python
from spry.i18n import I18nService
i18n = I18nService(locale_dir="locale")
builder.add_views(i18n=i18n)
```

No template:

```html
{% trans "Hello" %}
{% blocktranslate count=n %}You have {} message{% plural %}You have {} messages{% endblocktranslate %}
```
