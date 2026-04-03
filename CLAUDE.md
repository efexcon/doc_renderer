# sovaia-doc-renderer — Claude Code Instructions

## What This Repo Is

Standalone product for brand-conformant document rendering.
Takes Markdown + metadata + structured data from any source, applies centrally
managed brand templates, and outputs DOCX/PDF via Pandoc.

**This is an independent product (ADR-011), NOT tied to Workplace.**
Workplace may consume it via the Agent channel, but the renderer has no
dependency on Workplace or any other sovaia application.

## Design Principles (Non-Negotiable)

1. **Strict Isolation.** Every component works independently.
2. **Interface Contract.** Explicit APIs between components.
3. **Orchestrator Exclusivity.** Only orchestrators know dependencies.
4. **Semantic & Ontological Data.** Enrich data semantically where possible.
5. **Lean, Effective, Efficient.** Minimal complexity for maximum value.

## Layer Model

This repo is a **standalone product** (L3-adjacent / independent).

**Dependency rules:**
- May use: L1 (Platform Infrastructure) for deployment
- Must NOT depend on: L5 (Applications), L6 (Tenants)
- Consumed by: Workplace (Agent channel), external systems (API channel)

## Channel Architecture (ADR-011)

Input channels: File, Folder, API (FastAPI), MCP (V2), Agent (V2)
Output channels: File, Folder, API Response, MinIO/S3 (V2), MS Graph (V3)

## Decision Authority

The user is the architect. Claude implements.

**STOP and ask when:**
- New document types or brand templates
- Output format changes (beyond DOCX/PDF)
- New channels (MCP, Agent, Graph)
- API contract changes
- License integration decisions

**Claude may decide autonomously:**
- Bug fixes within existing patterns
- Code formatting and style
- YAML syntax fixes
- Commit message wording

## Repository Structure

```
src/
  pipeline.py        Assembler: Markdown + meta + items → assembled markdown
  render_docx.py     Renderer: assembled markdown → DOCX via Pandoc
  api.py             FastAPI wrapper (REST channel)
config/
  brands/
    kiinno-ag/
      brand.yaml     Brand identity, sender profiles, asset paths
      templates/     Reference DOCX templates per document type
      assets/        Logo, fonts
  document-types/
    angebot.yaml     Document type config (required fields, layout, assembly order)
    konzept.yaml
examples/
  {brand}/{doc-type}/{doc-id}/
    meta.yaml        Document metadata
    content.md       Markdown body (optional)
    items.json       Line items (optional, for angebot etc.)
build/               Generated output (gitignored)
```

## Tech Stack

- Python 3.12
- Pandoc (system dependency, renders Markdown → DOCX/PDF)
- FastAPI + Uvicorn (API channel)
- PyYAML (config/meta parsing)

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# CLI: assemble markdown
python src/pipeline.py examples/kiinno-ag/angebot/ANG-2026-031

# CLI: render DOCX
python src/render_docx.py examples/kiinno-ag/angebot/ANG-2026-031

# API server
uvicorn src.api:app --host 0.0.0.0 --port 3200

# Docker
docker build -t sovaia/doc-renderer:dev .
docker run -p 3200:3200 sovaia/doc-renderer:dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/render` | JSON body → DOCX file response |
| POST | `/render/upload` | Multipart upload (markdown + meta.yaml) → DOCX |
| GET | `/health` | Health check |
| GET | `/brands` | List available brands |
| GET | `/document-types` | List available document types |

## License

GPLv3 (see LICENSE). License-Agent stub prepared per ADR-011 / ADR-012.

## Related Repositories

| Repo | Relationship |
|------|-------------|
| `sovaia-contracts` | ADR-011, ADR-012, API specs |
| `sovaia-platform` | Deployment (Helm/ArgoCD) |
| `sovaia-web-core` | Workplace (consumes via Agent channel, V2) |

## Forbidden Patterns

- Hardcoded credentials or secrets
- Direct dependency on Workplace or web-core
- Committing build/ output
- Force-pushing to main

## Language

Documentation: German. Code/YAML comments: English or German.
