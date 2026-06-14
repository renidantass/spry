---
title: Troubleshooting
order: 10
description: Common errors and how to fix them
tags: troubleshooting, errors, debug
---

## ModuleNotFoundError

```bash
ModuleNotFoundError: No module named 'taskboard'
```

**Cause:** PYTHONPATH does not include the project's `src/` directory.

**Solution:**

```bash
# PowerShell
$env:PYTHONPATH="$PSScriptRoot\..\src;$PSScriptRoot\taskboard\src"
spry run --app taskboard.app:create_app
```

## Route returns 404

**Checklist:**
- The class has `@controller("/prefix")`
- The method has `@get`, `@post`, `@put`, `@patch` or `@delete`
- The controller is inside the application package
- The called route matches the prefix + method path

## Payload returns 422

This means the payload binding to the dataclass failed.

**Common causes:**
- Missing required fields
- Invalid types (sending string where int is expected)
- Field names diverging from the DTO

## MVC doesn't find view

- Check that `builder.add_views(...)` was called
- Check that the files exist inside `views/`
- The name passed in `self.view("home/index")` must match `views/home/index.html`

## Async handler doesn't work

**Cause:** Async handlers use `asyncio.run()` internally. If running in an environment with an active event loop (like ASGI), it may error.

**Solution:** Use synchronous handlers or ensure the middleware is also async.

## Database connection error

- Check that the database driver is installed (`spry[postgres]`, `spry[mysql]`, etc.)
- Check the connection URL in `appsettings.json`
- For production, configure `pool_size` to avoid creating connections per request
