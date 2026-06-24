---
title: Développement MVC
order: 3
description: Vues, layouts, partiels et HTML côté serveur
tags: mvc, vues, templates, html
---

## Contrôleur MVC

Utilisez `Controller` au lieu de `ControllerBase` pour les applications qui servent du HTML :

```python
from spry.controllers import Controller
from spry.routing import controller, get

@controller("/")
class HomeController(Controller):
    def __init__(self, view_renderer):
        super().__init__(view_renderer)

    @get("/")
    def index(self):
        return self.view("home/index", {"title": "Accueil"})
```

## Vues et Layouts

```
views/
  shared/
    _layout.html      → Layout principal avec {{ body }}
  home/
    index.html        → Vue rendue dans le layout
    _card.html        → Partiel (préfixe _)
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

### Vue

```html
<h1>{{ title }}</h1>
<p>{{ description }}</p>
```

## Moteur de Template

Spry est livré avec deux moteurs :

```python
# Moteur par défaut (zéro dépendance)
builder.add_views(engine="spry")

# Jinja2 (pip install spry-core[jinja2])
builder.add_views(engine="jinja2")
```

### Syntaxe du moteur Spry

```
{{ var }}              → Interpolation avec échappement
{{ var|upper }}        → Filters : upper, lower, default, safe
{% if cond %}...{% endif %}
{% for item in items %}...{% endfor %}
{% include "partial" %}
{% include "partial" without context %}
{# comment #}
```

### Partiels

Rendez des morceaux de HTML dans le contrôleur :

```python
todo_cards = HtmlString("".join(
    str(self.partial_view("home/_card", {"title": todo.title}))
    for todo in todos
))
return self.view("home/index", {"cards": todo_cards})
```

## i18n dans les Templates

```python
from spry.i18n import I18nService
i18n = I18nService(locale_dir="locale")
builder.add_views(i18n=i18n)
```

Dans le template :

```html
{% trans "Hello" %}
{% blocktranslate count=n %}You have {} message{% plural %}You have {} messages{% endblocktranslate %}
```
