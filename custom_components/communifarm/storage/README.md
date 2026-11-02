# storage

## Purpose

SQLite persistence, migrations, NFC pool — repositories only.

## How to use this directory

- Open when changing schema, migrations, repositories, or NFC pool tables.
- Do not block the event loop; access via repositories.
- Skills: storage, nfc-database, testing.

## Map

| path | layer | how / why |
|------|-------|-----------|
| `__init__.py` | `storage` | storage file `__init__.py`. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `batch_repository.py` | `storage` | SQLite repository for Communifarm batches and mix milestones. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `climate_repository.py` | `storage` | SQLite repository for climate nodes, bindings, and command intents. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `container_repository.py` | `storage` | SQLite repository for per-container production units + sale packs. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `culture_repository.py` | `storage` | SQLite repository for culture lots and media prep batches. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `inventory_repository.py` | `storage` | SQLite repository for inventory lots and employee badges. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `location_repository.py` | `storage` | SQLite repository for placement areas and zones. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `nfc_repository.py` | `storage` | SQLite repository for NFC check-ins and cross-object resolve. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `nfc_tag_pool_repository.py` | `storage` | SQLite repository for shipment / imported NFC tag pool (bind registry). — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `README.md` | `storage` | This directory map (dim1 Map + dim2 Feature index). |
| `repository.py` | `storage` | Store-backed repository for Communifarm domain state. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `sale_repository.py` | `storage` | SQLite repository for sales, line items, and cleanup events. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `sqlite_db.py` | `storage` | Communifarm SQLite database bootstrap and migrations. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `sqlite_repository.py` | `storage` | Shared SQLite connection, migrations, and process-wide lock. Repositories keep their own SQL and row mapping. Schema text stays in ``sqlite_ — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `tachometer_repository.py` | `storage` | SQLite repository for labeled vents and tachometer readings. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |
| `weight_repository.py` | `storage` | SQLite repository for Communifarm weight / material events. — Schema/repo change — migration + T0/T2; stable IDs ≠ entity names. |

## Feature index

| keywords / features | path |
|---------------------|------|
| storage | `__init__.py` |
| batch repository, storage, BatchRecord, BatchMilestone, BatchRepository, batch, repository, SQLite | `batch_repository.py` |
| climate repository, storage, ClimateRepository, climate, repository, SQLite | `climate_repository.py` |
| container repository, storage, ContainerRepository, container, repository, SQLite | `container_repository.py` |
| culture repository, storage, CultureRepository, culture, repository, SQLite, batch | `culture_repository.py` |
| inventory repository, storage, InventoryRepository, inventory, repository, SQLite | `inventory_repository.py` |
| location repository, storage, LocationRepository, location, repository, SQLite | `location_repository.py` |
| nfc repository, storage, NfcRepository, nfc, repository, SQLite | `nfc_repository.py` |
| nfc tag pool repository, storage, NfcTagPoolEntry, NfcTagPoolRepository, nfc, tag, pool, repository, SQLite | `nfc_tag_pool_repository.py` |
| repository, storage, CommunifarmRepository | `repository.py` |
| sale repository, storage, SaleRepository, sale, repository, SQLite | `sale_repository.py` |
| sqlite db, storage, SCHEMA_VERSION, MIGRATIONS, ensure_inventory_columns, db_path_for_config_dir, DB_LOCK, connect, apply_migrations, sqlite | `sqlite_db.py` |
| sqlite repository, storage, RepositoryClosedError, SqliteRepository, sqlite, repository | `sqlite_repository.py` |
| tachometer repository, storage, TachometerRepository, tachometer, repository, SQLite | `tachometer_repository.py` |
| weight repository, storage, WeightEventRepository, weight, repository, SQLite | `weight_repository.py` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
