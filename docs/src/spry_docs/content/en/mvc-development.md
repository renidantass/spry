---
title: MVC Development
order: 3
description: Views, layouts, partials and server-side HTML
tags: mvc, views, templates, html
---

## MVC Controller

Use `Controller` instead of `ControllerBase` for apps that serve HTML:

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

## Views and Layouts

```
views/
  shared/
    _layout.html      ? Main layout with {{ body }}
  home/
    index.html        ? View rendered inside the layout
    _card.html        ? Partial (prefix _)
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

Spry comes with two engines:

```python
# Default engine (zero dependencies)
builder.add_views(engine="spry")

# Jinja2 (pip install spry-core[jinja2])
builder.add_views(engine="jinja2")
```

### Spry Engine Syntax

```
{{ var }}              ? Interpolation with escaping
{{ var|upper }}        ? Filters: upper, lower, default, safe
{% if cond %}...{% endif %}
{% for item in items %}...{% endfor %}
{% include "partial" %}
{% include "partial" without context %}
{# comment #}
```

### Partials

Render HTML snippets in the controller:

```python
todo_cards = HtmlString("".join(
    str(self.partial_view("home/_card", {"title": todo.title}))
    for todo in todos
))
return self.view("home/index", {"cards": todo_cards})
```

## i18n in Templates

```python
from spry.i18n import I18nService
i18n = I18nService(locale_dir="locale")
builder.add_views(i18n=i18n)
```

In the template:

```html
{% trans "Hello" %}
{% blocktranslate count=n %}You have {} message{% plural %}You have {} messages{% endblocktranslate %}
```
