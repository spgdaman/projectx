## [2026-06-06] Category mapper + alerts refactor

### category_mapper.py
- Added `category_depth()` and `category_path()` static helpers
- All four tiers now prefer deeper (leaf) categories over root categories when scores are equal
- `MappingResult` now includes `category_depth` and `category_path` fields for debugging
- `_master_categories` cache uses 4-tuples `(cat, name, norm, depth)` instead of 3-tuples
- `_tier1_exact`: collects all matching CategoryMappings, returns the one with deepest master_category
- `_tier2_synonym`: collects all matching synonyms, returns the one with deepest master_category
- `_tier3_keyword`: collects all matching rules, sorts by (priority, depth) descending — ties broken by leaf specificity
- `_tier4_fuzzy`: adds depth bonus (max 3 pts) to effective score; threshold check still uses raw score
- `_load_keyword_rules` now `select_related` parent chain for depth calculation

### normalize.py
- Fast path now checks L2 → L1 → L0 category names against `cat_map` (previously L0 only)
- Staging rows with no `master_category` are **NOT deleted** — they remain in staging for manual review
- Only fully mapped rows (product created/updated + deal created/updated + master_category set) are deleted from staging
- Added docstring explaining the three-path category resolution and the keep-if-unmapped behaviour
- `_process_batch` now logs `Batch: deleted=N kept_unmapped=M` at INFO level

### process_alerts.py (management command)
- Moved to correct location: `core/management/commands/process_alerts.py`
- Rewritten to avoid O(deals × subscriptions) per-row DB queries
- Only processes deals scraped in last N hours (default 24, configurable via `--hours`)
- Deduplicates against AlertLog before sending — no double-sends within the lookback window
- Supports `--dry-run` mode (prints would-be alerts without sending or writing logs)
- Bulk creates `AlertLog` entries after the loop
- Proper error handling with per-sub and per-alert error counts

### alert_resolver.py
- Added `get_category_descendants(category)` — BFS over the `children` FK tree
- `category_scope` now includes products in child categories (full descendant tree, not just the direct category)
- All scopes now order by `discount_pct` descending (best deals first, not highest price first)
- Limits changed: paid users get top **5** products, free users get top **2**
- `product_scope` now guards against `subscription.product_id is None`

### subscriptions.py
- `update_product_subscription` no longer sets `subscription.category` directly
- Removed the direct `category = new_product.master_category` assignment that bypassed `Subscription.save()`
- The model's own `save()` override now enforces the `target_type='product'` invariant as designed

### New API endpoints
| Method | URL | Description |
|--------|-----|-------------|
| GET    | `/api/alerts/` | User's alert history (most recent first, `?limit=N`) |
| PATCH  | `/api/alerts/<id>/read/` | Mark a single alert as read |
| POST   | `/api/alerts/read-all/` | Mark all user alerts as read |
| GET    | `/api/alerts/unread-count/` | Returns `{"unread": N}` for notification badge |

### AlertLog model
- Added `is_read = BooleanField(default=False)` field
- Migration: `core/migrations/0020_add_alertlog_is_read.py`

### Celery wiring
- Added `process_alerts_task` shared task in `scrapers/tasks.py`
- `normalize_staging` task now calls `process_alerts_task.delay()` on completion
- Added `process-alerts` entry to `CELERY_BEAT_SCHEDULE` (`crontab(hour='*/4')`)
