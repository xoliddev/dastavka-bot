# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0.0] - 2026-11-13

A modernization release: the features and texts stay the same, but authorization,
correctness, tooling and tests were reworked.

### Security
- **Router-level authorization.** All admin handlers now live in `handlers/admin/`, whose root router has an `IsAdmin` filter on messages and callback queries. Before, only 11 of about 100 admin handlers checked permissions, so crafted callback data could trigger `deliver_order:`, `complete_order:`, `assign_courier:`, `confirm_assign:`, menu edits and deletes, settings, `final_reset_daily_id`, `get_daily_report` and others.
- **Courier router** guarded by `IsCourier` (role `courier` plus an active `couriers` row).
- **Ownership checks.** `cust_confirm_ok:` and `cust_confirm_no:` only work for the order's owner while it is `delivering`. `deliver_confirm:` and `view_delivery_task:` only work for the assigned courier, so customer name and phone no longer leak to other couriers. `confirm_cancel_order:` checks ownership too.
- **`ADMIN_IDS` is the single source of admin rights.** A stale `role = 'admin'` in the database grants nothing; removed admins are demoted on their next update. Notifications go to configured admins only.
- **Atomic, validated status transitions** (`transition_order_status`, `ORDER_TRANSITIONS`). Double clicks, stale buttons and forged callbacks cannot skip or revert statuses. Courier assignment requires an order in `processing` and an active courier.
- The customer cancellation window is enforced on the server.
- Customer-supplied name and phone are HTML-escaped in admin and courier messages.
- A fallback router answers rejected or unknown callbacks with an "access denied" alert and logs them.
- The Docker image runs as a non-root user.

### Fixed
- **Pagination.** Several "«" / "»" buttons produced callback data that no handler understood: the customer's top-level categories (`customer_view_cat_page:`), the customer's sub-category and product lists, the admin sub-category and product lists (`subcategory_page:N` / `product_page:N` without the category id), the admin courier list (`courier_page:`) and the courier's active deliveries. `build_pagination_keyboard` now requires a `page_callback` that encodes the full context, each list has a working page handler, and the courier lists render only the current page instead of every row.
- `fsm_courier_id` was defined twice, so the reactivation branch never ran and deactivated couriers could not be re-added. The duplicate is removed and the flow is covered by a test.
- `cb_restaurant_settings` was defined twice; one definition remains.
- **Race in `daily_id`.** `MAX(daily_id) + 1` inside the transaction could give two concurrent orders the same number. A counter row is now incremented atomically (`INSERT … ON CONFLICT DO UPDATE … RETURNING`); existing databases are migrated so numbering continues where it stopped.
- **Delivery zone** is now checked at checkout, not only when a location is set on `/start`.
- **Working hours** use `zoneinfo` with the `TIMEZONE` setting (default `Asia/Tashkent`) instead of a fixed UTC+5, and support shifts that cross midnight. The daily report and the "today / week / month" filters also use the café timezone instead of the database server's date.
- **Nominatim.** The placeholder User-Agent `YourBotName/1.0` was replaced by the configurable `NOMINATIM_USER_AGENT`; requests are limited to 1 per second and cached (LRU); network errors no longer break the flow.
- An order with two variations of the same product failed on `UNIQUE(order_id, product_id)`; the constraint now includes the variation.
- Selecting a saved address raised `TypeError` (wrong keyword argument).
- The "send location" button shown next to saved addresses (`go_to_location`) had no handler.
- Two lexicon keys used in code were missing (`category_not_found`, `no_enabled_languages_error`).
- Callbacks were sometimes answered twice (alert, then menu refresh), which Telegram rejects. A request middleware now lets only the first answer through.
- Admin text steps no longer crash when a photo or sticker is sent instead of text.
- The calendar no longer depends on OS locales being installed.
- Language selection only accepts supported language codes.

### Changed
- **aiogram 3.7 → 3.31.0** (latest stable on PyPI), asyncpg 0.32, redis 7.4, Python 3.12+.
- `handlers/admin_handlers.py` (2,700+ lines) split into `handlers/admin/{menu,categories,products,variations,orders,settings,team,group}.py`.
- Typed configuration with pydantic-settings (`core/config.py`); every option is documented in `.env.example`. `DATABASE_URL` and `REDIS_URL` are supported alongside the individual `POSTGRES_*` and `REDIS_*` variables.
- Structured logging (`LOG_FORMAT=text|json`) replaces `print()`; a dispatcher error handler logs unhandled exceptions.
- Graceful shutdown: the geocoder session, Redis, the PostgreSQL pool and the bot session are closed on SIGTERM or SIGINT.
- The schema is created or migrated idempotently on every startup (advisory lock, single transaction). `python database_setup.py` still works and uses the same settings.
- `python bot.py --check` boots up to Telegram authentication (config, PostgreSQL and schema, Redis, routers) and exits.
- Dockerfile based on `python:3.12-slim` with a non-root user and exec-form CMD; `docker-compose.yml` with PostgreSQL 16, Redis 7 (AOF), health checks and `depends_on: service_healthy`.
- `pyproject.toml` with ruff (lint and format) and pytest configuration; the codebase is formatted with ruff.

### Added
- Test suite (pytest + pytest-asyncio): unit tests, integration tests against a real PostgreSQL 16 (Docker or `TEST_DATABASE_URL`), and handler tests that feed `Update` objects into the real dispatcher with a mocked Bot session, including paging through every long list.
- A callback-routing test: every `callback_data` template in the code is collected statically and must be accepted by a real handler, so buttons that lead nowhere cannot come back.
- GitHub Actions CI: ruff, pytest on Python 3.12 and 3.13 with a PostgreSQL service container, and a Docker build plus `--check` against the compose services.
- `README.uz.md` (Uzbek), security and architecture documentation, this changelog.

### Removed
- `db_helpers.check_permission` (replaced by router filters).
- `python-dotenv` (pydantic-settings reads `.env`); OS `locales`/`tzdata` packages in the image (the `tzdata` PyPI package is used).

## [1.0.0]

Initial version.
