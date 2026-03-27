from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pipeline import run as assemble_run


def ensure_pandoc() -> str:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError("pandoc not found in PATH")
    return pandoc


def resolve_reference_doc(config_root: Path, brand: str, doc_type: str) -> Path | None:
    candidate = config_root / "brands" / brand / "templates" / f"{doc_type}.docx"
    if candidate.exists():
        return candidate
    return None


def render_docx(example_root: str, config_root: str = "config", output_dir: str = "build") -> Path:
    example_path = Path(example_root)
    brand = example_path.parts[-3]
    doc_type = example_path.parts[-2]

    assembled_path = assemble_run(example_root, config_root=config_root, output_dir=output_dir)
    build_dir = Path(output_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    pandoc = ensure_pandoc()
    output_path = build_dir / f"{assembled_path.stem.replace('_assembled', '')}.docx"

    cmd = [pandoc, str(assembled_path), "-o", str(output_path)]

    reference_doc = resolve_reference_doc(Path(config_root), brand, doc_type)
    if reference_doc is not None:
        cmd.extend([f"--reference-doc={reference_doc}"])

    subprocess.run(cmd, check=True)
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render an example job to DOCX using pandoc")
    parser.add_argument("example_root", help="Path to example job folder")
    parser.add_argument("--config-root", default="config", help="Path to config root")
    parser.add_argument("--output-dir", default="build", help="Path to build output directory")
    args = parser.parse_args()

    out = render_docx(args.example_root, config_root=args.config_root, output_dir=args.output_dir)
    print(out)
