"""FastAPI wrapper for doc_renderer pipeline (ADR-011 API channel)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure src/ is importable when running as package
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import build_job, assemble_markdown, load_yaml  # noqa: E402
from render_docx import ensure_pandoc, resolve_reference_doc  # noqa: E402

import subprocess  # noqa: E402

CONFIG_ROOT = Path(__file__).resolve().parent.parent / "config"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="SOVAIA Document Renderer",
    version="1.0.0",
    description="Brand-conformant document rendering — Markdown + metadata → DOCX",
)


# --- Models ---

class RenderRequest(BaseModel):
    brand: str
    document_type: str
    document_id: str
    meta: dict[str, Any]
    content: str = ""
    items: list[dict[str, Any]] = []


# --- Helpers ---

def _render_to_docx(assembled_md: str, brand: str, doc_type: str, doc_id: str) -> Path:
    """Write assembled markdown to temp dir and render via Pandoc."""
    pandoc = ensure_pandoc()
    tmp = Path(tempfile.mkdtemp(prefix="docrender_"))
    md_path = tmp / f"{doc_id}_assembled.md"
    md_path.write_text(assembled_md, encoding="utf-8")
    docx_path = tmp / f"{doc_id}.docx"

    cmd = [pandoc, str(md_path), "-o", str(docx_path)]
    ref = resolve_reference_doc(CONFIG_ROOT, brand, doc_type)
    if ref is not None:
        cmd.append(f"--reference-doc={ref}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Pandoc failed: {result.stderr}")
    return docx_path


# --- Endpoints ---

@app.get("/")
def root():
    """Serve the demo UI."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
def health():
    return {"status": "ok", "service": "doc-renderer"}


@app.get("/brands")
def list_brands():
    brands_dir = CONFIG_ROOT / "brands"
    if not brands_dir.exists():
        return {"brands": []}
    brands = []
    for d in sorted(brands_dir.iterdir()):
        if d.is_dir() and (d / "brand.yaml").exists():
            cfg = load_yaml(d / "brand.yaml")
            brands.append({
                "key": d.name,
                "name": cfg.get("brand", {}).get("name", d.name),
            })
    return {"brands": brands}


@app.get("/document-types")
def list_document_types():
    dt_dir = CONFIG_ROOT / "document-types"
    if not dt_dir.exists():
        return {"document_types": []}
    types = []
    for f in sorted(dt_dir.glob("*.yaml")):
        cfg = load_yaml(f)
        dt = cfg.get("document_type", {})
        types.append({
            "key": dt.get("key", f.stem),
            "label": dt.get("label", f.stem),
        })
    return {"document_types": types}


@app.post("/render")
def render(req: RenderRequest):
    """Render a document from JSON payload, return DOCX."""
    # Validate brand and document type exist
    brand_path = CONFIG_ROOT / "brands" / req.brand / "brand.yaml"
    if not brand_path.exists():
        raise HTTPException(status_code=404, detail=f"Brand not found: {req.brand}")
    dt_path = CONFIG_ROOT / "document-types" / f"{req.document_type}.yaml"
    if not dt_path.exists():
        raise HTTPException(status_code=404, detail=f"Document type not found: {req.document_type}")

    brand_cfg = load_yaml(brand_path)
    dt_cfg = load_yaml(dt_path)

    # Ensure meta has required fields
    meta = {**req.meta, "document_id": req.document_id}

    job_data = {
        "job": {
            "id": req.document_id,
            "type": req.document_type,
            "brand": req.brand,
            "output_formats": ["docx"],
        },
        "metadata": meta,
        "brand": brand_cfg,
        "document_type": dt_cfg,
        "content": req.content,
        "line_items": req.items,
    }

    assembled = assemble_markdown(job_data)
    docx_path = _render_to_docx(assembled, req.brand, req.document_type, req.document_id)

    return FileResponse(
        path=str(docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{req.document_id}.docx",
    )


@app.post("/render/upload")
async def render_upload(
    markdown: UploadFile = File(...),
    meta: UploadFile = File(...),
    brand: str = Form(...),
    document_type: str = Form(...),
):
    """Render from uploaded markdown + meta.yaml files."""
    # Validate brand and document type
    brand_path = CONFIG_ROOT / "brands" / brand / "brand.yaml"
    if not brand_path.exists():
        raise HTTPException(status_code=404, detail=f"Brand not found: {brand}")
    dt_path = CONFIG_ROOT / "document-types" / f"{document_type}.yaml"
    if not dt_path.exists():
        raise HTTPException(status_code=404, detail=f"Document type not found: {document_type}")

    import yaml
    meta_content = await meta.read()
    meta_data = yaml.safe_load(meta_content) or {}
    md_content = (await markdown.read()).decode("utf-8")
    doc_id = meta_data.get("document_id", "upload")

    brand_cfg = load_yaml(brand_path)
    dt_cfg = load_yaml(dt_path)

    job_data = {
        "job": {"id": doc_id, "type": document_type, "brand": brand, "output_formats": ["docx"]},
        "metadata": meta_data,
        "brand": brand_cfg,
        "document_type": dt_cfg,
        "content": md_content,
        "line_items": [],
    }

    assembled = assemble_markdown(job_data)
    docx_path = _render_to_docx(assembled, brand, document_type, doc_id)

    return FileResponse(
        path=str(docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{doc_id}.docx",
    )


# Mount static files last so API routes take precedence
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
