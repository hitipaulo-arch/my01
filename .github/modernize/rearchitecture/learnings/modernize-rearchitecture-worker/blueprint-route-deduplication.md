# Blueprint Route Deduplication

Blueprint routes should be referenced with qualified endpoint names instead of factory aliases when the route map must contain one rule per path and method.

## What Happened
In my01 phase4, admin aliases registered with `add_url_rule` duplicated paths already owned by the admin blueprint. Templates were updated to `admin.*` and the aliases were removed; the final map had 39 rules and zero duplicate `(path, methods)` keys.

## Takeaway
Preserve public Python imports with simple aliases, but do not preserve legacy `url_for` aliases when they create duplicate Flask rules. Update templates and redirects to qualified blueprint endpoints.

## History
- 2026-09-28 (my01/phase4-tools-webhook): initial