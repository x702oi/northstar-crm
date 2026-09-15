from __future__ import annotations

import hashlib
import json
from pathlib import Path

import frappe
from frappe.utils.file_manager import get_file


TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".xml", ".log"}


def extract_document_text(asset_name: str):
    """Extract safe text formats; provide an extension point for OCR/PDF/Office workers."""
    asset = frappe.get_doc("CRM Document Asset", asset_name)
    try:
        asset.db_set("extraction_status", "Processing")
        file_name, content = get_file(asset.file_url)
        extension = Path(file_name).suffix.lower()
        raw_content = content if isinstance(content, bytes) else content.encode("utf-8")
        checksum = hashlib.sha256(raw_content).hexdigest()
        if extension not in TEXT_EXTENSIONS:
            asset.db_set(
                {
                    "checksum_sha256": checksum,
                    "extraction_status": "Manual Review",
                    "extraction_error": f"No built-in extractor for {extension or 'unknown'} files.",
                    "derived_metadata": {
                        "extension": extension,
                        "extractor": None,
                        "requires_external_processor": True,
                    },
                }
            )
            return {"asset": asset_name, "status": "manual_review", "extension": extension}

        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        if extension == ".json":
            content = json.dumps(json.loads(content), ensure_ascii=False, indent=2)

        max_chars = frappe.db.get_single_value("CRM Settings", "max_extracted_text_chars") or 250000
        text = content[: int(max_chars)]
        asset.db_set(
            {
                "checksum_sha256": checksum,
                "extracted_text": text,
                "extraction_status": "Completed",
                "extraction_error": None,
                "character_count": len(text),
                "derived_metadata": {
                    "extension": extension,
                    "extractor": "northstar-plain-text-v1",
                    "truncated": len(content) > len(text),
                },
            }
        )
        return {"asset": asset_name, "status": "completed", "character_count": len(text)}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Northstar CRM document extraction")
        asset.db_set(
            {
                "extraction_status": "Failed",
                "extraction_error": "Extraction failed. Ask an administrator to review the Error Log.",
            }
        )
        raise
