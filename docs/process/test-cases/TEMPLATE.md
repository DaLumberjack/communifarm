# <process name> — test cases

Operator doc: `repos/communifarm/docs/process/<process>.md`

Quality oracle: `docs/intermediate/cea-quality-process.md`

## <step id> — <operator step in plain language>

When you <do this human step>, these tests verify <observable result>.

| field | value |
|-------|-------|
| CQA | what quality this step protects |
| CPP / gate | the parameter or predecessor that must be true |
| acceptance | inclusive limit, from the process doc |
| flaw this case is built to catch | the logic error that would still look successful |
| loop | `none` \| `control` \| `process` \| `iteration` |
| stage | T0 / T1 / T2 / T3 |
| pytest or spec | `tests/test_<module>.py::test_<name>` |
| pass means | what the operator can rely on |
| pass does not mean | live hardware, other stages, regulatory release |
| related batches | other lots the same flaw would touch |

### Setup

Starting records and operator inputs. Use normal process values.

### Steps

1. Operator action, in process order.
2. The violation case (wrong order, stale reading, second submit, skipped gate).

### Expected record

| object | field | expected |
|--------|-------|----------|
| event or entity | actual CPP | value or absent row |

Rejected steps leave no success event.

### Sources

- process doc section
- intake source id from `docs/intake/2026-10-01-cea-quality-published-sources.md` (S1–S9 as applicable)
