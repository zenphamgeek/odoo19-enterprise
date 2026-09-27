#!/usr/bin/env python3
import argparse
import ast
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
POS_REACT = ROOT / "insilos/apps/pos_react"
OUTPUT = POS_REACT / "inventory.json"
EXPECTED_DEPENDENCIES = 66
OWNED_ORACLES = {
    "pos_avatax": ["insilos/apps/pos_react/tests/test_pos_avatax_parity.py"],
    "whatsapp_pos": ["insilos/apps/pos_react/tests/test_whatsapp_pos_receipt_parity.py"],
}


def manifest(path):
    return ast.literal_eval(path.read_text(encoding="utf-8"))


def extension_classification(module, data):
    root = module.parent
    classes = set()
    assets = data.get("assets", {})
    paths = [entry for entries in assets.values() for entry in entries if isinstance(entry, str)]
    if assets:
        classes.add("asset_injection")
    if data.get("data") or data.get("demo"):
        classes.add("manifest_data")
    if any(root.glob("static/src/**/*.js")):
        classes.add("javascript")
    if any(root.glob("static/src/**/*.xml")):
        classes.add("qweb")
    if any(root.glob("models/**/*.py")) or any(root.glob("controllers/**/*.py")):
        classes.add("python")
    name = root.name
    if any(token in name for token in ("adyen", "cash", "dpopay", "glory", "imin", "mercado", "mollie", "payment", "pine_labs", "qfpay", "razorpay", "safaricom", "stripe", "tyro", "viva")):
        classes.add("payment")
    if "iot" in name or "pricer" in name:
        classes.add("hardware")
    if name.startswith("l10n_"):
        classes.add("localization_fiscal")
    if not classes:
        classes.add("dependency_only")
    return sorted(classes), sorted(paths)


def oracle_paths(root, owned_oracles=None):
    paths = []
    for pattern in ("tests/test_*.py", "static/tests/**/*.js"):
        paths.extend(str(path.relative_to(ROOT)) for path in root.glob(pattern))
    paths.extend((OWNED_ORACLES if owned_oracles is None else owned_oracles).get(root.name, []))
    return sorted(set(paths))


def module_root(name):
    matches = [ROOT / "insilos" / boundary / name for boundary in ("addons", "apps")]
    matches = [path for path in matches if path.is_dir()]
    if len(matches) != 1:
        raise ValueError(f"module {name!r} resolved to {len(matches)} directories")
    return matches[0]


def expand_bundle(module_name, bundle_name, manifests, stack=()):
    key = (module_name, bundle_name)
    if key in stack:
        raise ValueError(f"cyclic asset include: {bundle_name}")
    entries = manifests[module_name].get("assets", {}).get(bundle_name)
    if entries is None:
        raise ValueError(f"unknown asset bundle: {bundle_name}")
    files = []
    for entry in entries:
        if isinstance(entry, (list, tuple)):
            operation, target, *arguments = entry
            if operation == "include":
                owner = target.split(".", 1)[0]
                files.extend(expand_bundle(owner, target, manifests, stack + (key,)))
                continue
            elif operation in ("remove", "replace"):
                pattern = target.lstrip("/").split("/", 1)
                if len(pattern) != 2:
                    raise ValueError(f"invalid remove target: {target}")
                root = module_root(pattern[0])
                removed = set(root.glob(pattern[1]))
                files = [path for path in files if path not in removed]
                if operation == "remove":
                    continue
            elif operation not in ("before", "after"):
                raise ValueError(f"unsupported asset directive: {operation}")
            target = arguments[-1] if arguments else target
            pattern = target.lstrip("/").split("/", 1)
            if len(pattern) != 2:
                raise ValueError(f"invalid asset pattern: {target}")
            matches = sorted(path for path in module_root(pattern[0]).glob(pattern[1]) if path.is_file())
            if not matches:
                raise ValueError(f"asset pattern matched no files: {target}")
            files.extend(matches)
            continue
        pattern = entry.lstrip("/").split("/", 1)
        if len(pattern) != 2:
            raise ValueError(f"invalid asset pattern: {entry}")
        matches = sorted(path for path in module_root(pattern[0]).glob(pattern[1]) if path.is_file())
        if not matches:
            raise ValueError(f"asset pattern matched no files: {entry}")
        files.extend(matches)
    return list(dict.fromkeys(files))


def baseline():
    manifests = {}
    for boundary in ("addons", "apps"):
        for path in (ROOT / "insilos" / boundary).glob("*/__manifest__.py"):
            manifests[path.parent.name] = manifest(path)
    files = expand_bundle("point_of_sale", "point_of_sale.assets_prod", manifests)
    content = b"".join(path.read_bytes() for path in files)
    return {
        "bundle": "point_of_sale.assets_prod",
        "expanded_file_count": len(files),
        "expanded_source_bytes": len(content),
        "expanded_source_gzip_bytes": len(gzip.compress(content, mtime=0)),
    }


def capability(module_name, owner, owned_oracles):
    root = module_root(module_name)
    data = manifest(root / "__manifest__.py")
    classes, _assets = extension_classification(root / "__manifest__.py", data)
    oracles = oracle_paths(root, owned_oracles)
    return {
        "module": module_name,
        "owner": owner,
        "dependency": data.get("depends", []),
        "extension_mechanism": classes,
        "oracle_tests": oracles,
        "status": "Inventoried" if oracles else "Blocked",
        "blocker": None if oracles else "missing_oracle",
    }


def generate(owned_oracles=OWNED_ORACLES):
    dependencies = []
    for boundary in ("addons", "apps"):
        for path in sorted((ROOT / "insilos" / boundary).glob("*/__manifest__.py")):
            if path.parent == POS_REACT:
                continue
            data = manifest(path)
            if "point_of_sale" not in data.get("depends", []):
                continue
            classes, assets = extension_classification(path, data)
            dependencies.append({
                "module": path.parent.name,
                "boundary": boundary,
                "extension_classification": classes,
                "oracle_paths": oracle_paths(path.parent),
                "static_assets": assets,
            })
    dependencies.sort(key=lambda item: (item["boundary"], item["module"]))
    if len(dependencies) != EXPECTED_DEPENDENCIES:
        raise ValueError(f"expected {EXPECTED_DEPENDENCIES} direct dependencies, found {len(dependencies)}")
    enterprise = [capability(item["module"], "Enterprise", owned_oracles) for item in dependencies if item["boundary"] == "apps"]
    capabilities = [
        capability("point_of_sale", "core", owned_oracles),
        capability("pos_sale", "pos_sale", owned_oracles),
        capability("pos_restaurant", "pos_restaurant", owned_oracles),
        *enterprise,
    ]
    payload = {
        "schema_version": 2,
        "direct_dependency_count": len(dependencies),
        "dependencies": dependencies,
        "capabilities": capabilities,
        "baseline": baseline(),
    }
    if not capabilities:
        raise ValueError("capability inventory is empty")
    return payload


def serialized(payload):
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail unless inventory.json matches current sources")
    parser.add_argument("--baseline", action="store_true", help="print source-only expanded bundle baseline")
    args = parser.parse_args()
    if args.baseline:
        print(json.dumps(baseline(), sort_keys=True))
    else:
        result = generate()
        current = serialized(result)
        if args.check:
            if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != current:
                raise SystemExit("inventory gate failed: run generate_inventory.py")
            print(f"Inventory gate passed: {result['direct_dependency_count']} dependencies")
        else:
            OUTPUT.write_text(current, encoding="utf-8")
            print(f"Wrote {OUTPUT.relative_to(ROOT)}: {result['direct_dependency_count']} dependencies")
