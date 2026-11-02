# dashboard

## Purpose

Generated dashboard / Lovelace model helpers.

## How to use this directory

- Read **Feature index** for task keywords, then **Map** for how/why before opening files.
- This directory is primarily `ui`-oriented; stay in-layer unless adapters require a bridge.
- Update this README when adding/removing public files or symbols (`py scripts/generate_directory_readmes.py`).

## Map

| path | layer | how / why |
|------|-------|-----------|
| `__init__.py` | `ui` | ui file `__init__.py`. — Operator-visible UI/assets — verify T1 if behavior changes. |
| `builder.py` | `ui` | ui file `builder.py`. — Operator-visible UI/assets — verify T1 if behavior changes. |
| `layout_png.py` | `ui` | Raster copy of the operator schematic. Picture-elements loads the background with an image tag. An SVG from ``/local/`` is often served as t — Operator-visible UI/assets — verify T1 if behavior changes. |
| `provisioner.py` | `ui` | Provision a Communifarm-managed Lovelace dashboard via lovelace storage. — Operator-visible UI/assets — verify T1 if behavior changes. |
| `README.md` | `ui` | This directory map (dim1 Map + dim2 Feature index). |

## Feature index

| keywords / features | path |
|---------------------|------|
| ui | `__init__.py` |
| builder, ui, DashboardBuilder | `builder.py` |
| layout png, ui, SCALE, WIDTH, HEIGHT, render_operator_layout_png, png_rgb, layout, png | `layout_png.py` |
| provisioner, ui, resolve_bindings, async_provision_dashboard | `provisioner.py` |

<!-- generated/maintained per .agents/skills/directory-readme/SKILL.md -->
