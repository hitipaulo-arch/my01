# Flask Factory Extensions

Application extensions must be instantiated unbound and initialized inside `create_app`.

## What Happened
In this project, the installed Flask-Limiter version requires `key_func` in its constructor. The shared extension therefore uses the existing remote-address key function before `init_app`, while CSRF and Cache remain unbound. Legacy routes stay in `app.py` during phase 1 and use the factory-provided cache instance.

## Takeaway
When extracting Flask bootstrap incrementally, keep route decorators in the legacy module until their blueprint moves are complete, but move middleware and error handlers to the factory so each application instance registers them once.

## History
- 2026-09-28 (my01/phase1): initial