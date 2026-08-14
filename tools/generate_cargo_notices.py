#!/usr/bin/env python3
"""Generate compact notices for locked Cargo dependencies.

The wheel's CycloneDX SBOM is the complete component inventory. This file records the reviewed
license choice for each Cargo SPDX expression and bundles only text not already supplied by the
project's Apache-2.0 license, plus any upstream NOTICE files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "gerrychain-core" / "Cargo.toml"
OUTPUT = ROOT / "THIRD_PARTY_NOTICES.txt"

# An empty tuple selects Apache-2.0, whose text is already bundled as LICENSE.rustworkx.
# Any new expression fails generation until its distribution terms are reviewed.
LICENSE_POLICY = {
    "(MIT OR Apache-2.0) AND Unicode-3.0": ("Unicode-3.0",),
    "0BSD OR MIT OR Apache-2.0": (),
    "Apache-2.0": (),
    "Apache-2.0 OR MIT": (),
    "Apache-2.0 WITH LLVM-exception": ("Apache-2.0 WITH LLVM-exception",),
    "Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT": (),
    "Apache-2.0/MIT": (),
    "BSD-2-Clause": ("BSD-2-Clause",),
    "BSD-2-Clause OR Apache-2.0 OR MIT": (),
    "LGPL-3.0-or-later OR MPL-2.0": ("MPL-2.0",),
    "MIT": ("MIT",),
    "MIT OR Apache-2.0": (),
    "MIT OR Apache-2.0 OR LGPL-2.1-or-later": (),
    "MIT OR Zlib OR Apache-2.0": (),
    "MIT/Apache-2.0": (),
    "Unlicense OR MIT": ("MIT",),
    "Zlib": ("Zlib",),
    "Zlib OR Apache-2.0 OR MIT": (),
}

# Package-specific filenames preserve copyright and attribution text. Pinning the version makes
# a dependency update stop until the replacement archive and its notices have been reviewed.
REQUIRED_LICENSE_FILES = {
    ("foldhash", "0.1.5"): {"Zlib": "LICENSE"},
    ("libm", "0.2.16"): {"MIT": "LICENSE.txt"},
    ("memchr", "2.8.3"): {"MIT": "LICENSE-MIT"},
    ("numpy", "0.29.0"): {"BSD-2-Clause": "LICENSE"},
    ("priority-queue", "2.7.0"): {"MPL-2.0": "MPL-2.0.txt"},
    ("quick-xml", "0.37.5"): {"MIT": "LICENSE-MIT.md"},
    ("simd-adler32", "0.3.10"): {"MIT": "LICENSE.md"},
    ("target-lexicon", "0.13.5"): {"Apache-2.0 WITH LLVM-exception": "LICENSE"},
    ("unicode-ident", "1.0.24"): {"Unicode-3.0": "LICENSE-UNICODE"},
    ("zmij", "1.0.23"): {"MIT": "LICENSE-MIT"},
}


def cargo_metadata() -> dict[str, object]:
    result = subprocess.run(
        [
            "cargo",
            "metadata",
            "--locked",
            "--all-features",
            "--format-version",
            "1",
            "--manifest-path",
            str(MANIFEST),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def resolved_dependencies(metadata: dict[str, object]) -> list[dict[str, object]]:
    resolve = metadata["resolve"]
    assert isinstance(resolve, dict)
    root_id = resolve["root"]
    nodes = {node["id"]: node for node in resolve["nodes"]}
    reachable = {root_id}
    pending = [root_id]
    while pending:
        package_id = pending.pop()
        for dependency in nodes[package_id]["dependencies"]:
            if dependency not in reachable:
                reachable.add(dependency)
                pending.append(dependency)

    packages = {
        package["id"]: package
        for package in metadata["packages"]
        if package["id"] in reachable and package["id"] != root_id
    }
    return sorted(packages.values(), key=lambda package: (package["name"], package["version"]))


def source_url(package: dict[str, object]) -> str:
    source = str(package.get("source") or "path dependency")
    if source == "registry+https://github.com/rust-lang/crates.io-index":
        return f"https://crates.io/crates/{package['name']}/{package['version']}"
    return source


def add_document_group(
    sections: list[str],
    heading: str,
    documents: list[tuple[str, str, str, Path]],
) -> None:
    sections.extend(["=" * 100, heading, "", "Packages:"])
    packages = sorted({(name, version, source) for name, version, source, _ in documents})
    sections.extend(f"- {name} {version}: {source}" for name, version, source in packages)
    sections.append("")

    by_content: dict[str, list[tuple[str, str, Path]]] = {}
    for name, version, _, path in documents:
        content = path.read_text(encoding="utf-8", errors="replace").rstrip()
        by_content.setdefault(content, []).append((name, version, path))
    for content, owners in sorted(by_content.items(), key=lambda item: item[1][0][:2]):
        applies_to = ", ".join(
            f"{name} {version} ({path.name})" for name, version, path in sorted(owners)
        )
        sections.extend([f"--- Applies to: {applies_to} ---", content, ""])


def render() -> str:
    groups: dict[str, list[tuple[str, str, str, Path]]] = {}
    notices: list[tuple[str, str, str, Path]] = []
    errors: list[str] = []

    for package in resolved_dependencies(cargo_metadata()):
        name = str(package["name"])
        version = str(package["version"])
        key = (name, version)
        expression = str(package.get("license") or "not specified")
        if expression not in LICENSE_POLICY:
            errors.append(f"{name} {version}: unreviewed license expression {expression}")
            continue

        required_groups = set(LICENSE_POLICY[expression])
        configured_files = REQUIRED_LICENSE_FILES.get(key, {})
        if set(configured_files) != required_groups:
            errors.append(
                f"{name} {version}: expected files for {sorted(required_groups)}, "
                f"configured {sorted(configured_files)}"
            )
            continue

        package_dir = Path(str(package["manifest_path"])).parent
        source = source_url(package)
        for group, filename in configured_files.items():
            path = package_dir / filename
            if not path.is_file():
                errors.append(f"{name} {version}: missing {filename}")
            else:
                groups.setdefault(group, []).append((name, version, source, path))

        notices.extend(
            (name, version, source, path)
            for path in package_dir.iterdir()
            if path.is_file() and path.name.upper().startswith("NOTICE")
        )

    if errors:
        raise RuntimeError("Cargo license review failed:\n- " + "\n- ".join(errors))

    sections = [
        "THIRD-PARTY RUST NOTICES",
        "",
        "Generated from gerrychain-core/Cargo.lock by tools/generate_cargo_notices.py.",
        "The wheel's CycloneDX SBOM is the complete Cargo component and license inventory.",
        "Dependencies offering Apache-2.0 are distributed under that option; its license text",
        "is bundled once as LICENSE.rustworkx. The sections below contain only additional",
        "selected license terms and upstream NOTICE files.",
        "",
    ]
    for heading, documents in sorted(groups.items()):
        add_document_group(sections, heading, documents)
    if notices:
        add_document_group(sections, "UPSTREAM NOTICE FILES", notices)
    return "\n".join(sections).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed notices are stale"
    )
    args = parser.parse_args()
    content = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            print(f"{OUTPUT.name} is stale; regenerate it with {__file__}", file=sys.stderr)
            return 1
    else:
        OUTPUT.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
