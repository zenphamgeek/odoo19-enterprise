#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

BUNDLE = "point_of_sale.assets_prod"
SCRIPT_PATH = Path(globals().get("__file__", "insilos/apps/pos_react/tools/collect_compiled_bundle.py")).resolve()
SCHEMA = SCRIPT_PATH.with_name("compiled_bundle_evidence.schema.json")


def canonical_asset_url(url):
    path = urlsplit(url).path
    if path.startswith("/insilos/assets/"):
        return "/web/assets/" + path.removeprefix("/insilos/assets/")
    return path


def parse_links(links):
    urls = []
    for link in links:
        url = link[0] if isinstance(link, (list, tuple)) else link
        if isinstance(url, str) and url.startswith("/"):
            urls.append(canonical_asset_url(url))
    if not urls:
        raise ValueError("compiled bundle produced no attachment URLs")
    return urls


def collect(orm_env, collected_at=None):
    links = orm_env["ir.qweb"]._get_asset_links(BUNDLE, debug=False)
    linked_urls = parse_links(links) if links else []
    bundle = orm_env["ir.qweb"]._get_asset_bundle(BUNDLE, css=True, js=True, debug_assets=False)
    attachments = []
    if any(url.endswith(".css") for url in linked_urls):
        css = bundle.css()
        attachments.extend(css if isinstance(css, (list, tuple)) else [css])
    if any(url.endswith(".js") for url in linked_urls) or not linked_urls:
        attachments.append(bundle.js())
    attachments = [attachment for attachment in attachments if attachment]
    if not attachments:
        raise ValueError("compiled bundle produced no attachments")
    artifacts = []
    for attachment in attachments:
        url = attachment.url
        raw = attachment.raw or b""
        artifacts.append({
            "url": url,
            "name": attachment.name,
            "mimetype": attachment.mimetype,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    return {
        "schema_version": 1,
        "bundle": BUNDLE,
        "database": orm_env.cr.dbname,
        "collected_at": collected_at or datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts,
    }


def validate(payload):
    required = {"schema_version", "bundle", "database", "collected_at", "artifacts"}
    if set(payload) != required or payload["schema_version"] != 1 or payload["bundle"] != BUNDLE:
        raise ValueError("invalid compiled bundle evidence header")
    if not isinstance(payload["database"], str) or not payload["database"] or not isinstance(payload["collected_at"], str):
        raise ValueError("invalid compiled bundle evidence metadata")
    if not isinstance(payload["artifacts"], list) or not payload["artifacts"]:
        raise ValueError("compiled bundle evidence has no artifacts")
    artifact_keys = {"url", "name", "mimetype", "bytes", "sha256"}
    for artifact in payload["artifacts"]:
        if set(artifact) != artifact_keys or not artifact["url"].startswith("/") or artifact["bytes"] <= 0:
            raise ValueError("invalid compiled bundle artifact")
        if len(artifact["sha256"]) != 64 or any(char not in "0123456789abcdef" for char in artifact["sha256"]):
            raise ValueError("invalid compiled bundle artifact digest")
    return payload


def emit(payload, output=None):
    content = json.dumps(validate(payload), indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def main(argv=None, orm_env=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.environ.get("POS_REACT_BUNDLE_EVIDENCE"))
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    if args.check:
        validate(json.loads(args.check.read_text(encoding="utf-8")))
        print(f"Compiled bundle evidence gate passed: {args.check}")
        return
    if orm_env is None:
        raise SystemExit("ORM env required; run through insilos-bin shell or pass orm_env")
    emit(collect(orm_env), args.output)


if __name__ == "__main__":
    main(argv=[] if "env" in globals() else None, orm_env=globals().get("env"))
