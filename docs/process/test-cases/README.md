# Test cases

These files are the operator-facing proof behind a human process step.

A case is written with the test, from the process doc and from `docs/intermediate/cea-quality-process.md`. It is not a dump of pytest names after a green run.

## When you are doing this step

User docs should be able to say, in plain language:

> When you do **\<operator step\>**, these tests verify **\<observable result\>**.

That sentence lives in each case file. Link the case from the process doc when that process changes.

## Rules

| rule | meaning |
|------|---------|
| oracle | expected result comes from the process doc and the quality note |
| one case file per process | `test-cases/<process-slug>.md`, sections per step |
| same change as the test | a new behavior without a case section is unfinished |
| pass language | state what a pass guarantees for the operator |
| non-claim | state what a pass does not prove (live hardware, GMP certification, untested stages) |
| loops | each control, process, or iteration loop has a flaw case, not only a happy trip |

Copy `TEMPLATE.md` into the process file on first use. Do not leave the template as if it were a real case.

## Index

Add a row when the first real case for that process exists.

| process | case file | operator doc |
|---------|-----------|--------------|
| Air-exchange tachometer | [air-exchange-tachometer.md](./air-exchange-tachometer.md) | [hardware/air-exchange-tachometer.md](../../hardware/air-exchange-tachometer.md) |
