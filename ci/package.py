"""Build the collection with the pinned platform release coordinates."""

import shutil
import subprocess
from pathlib import Path

import yaml
from release import ROOT, identity, platform, reproducible

version, _ = identity()
release = platform()
values = ROOT / "playbooks/charts/agentos/values.yaml"
if not values.exists():
    raise FileNotFoundError("Run ci/platform.py to extract the verified platform chart defaults")
build = ROOT / ".cache/collection"
shutil.rmtree(build, ignore_errors=True)
shutil.copytree(ROOT, build, ignore=shutil.ignore_patterns(".git", ".cache", "dist", "__pycache__"))
for name in ("deploy", "environments"):
    path = build / "playbooks" / name / "vars.yaml"
    variables = yaml.safe_load(path.read_text())
    variables.update(
        delivery_version=release["version"],
        delivery_revision=release["revision"],
        agentos_image_registry=release["registry"],
    )
    path.write_text(yaml.safe_dump(variables, sort_keys=False))
output = ROOT / "dist"
subprocess.run(
    ["ansible-galaxy", "collection", "build", str(build), "--output-path", str(output), "--force"],
    check=True,
)
archive = Path(output, f"agentos-platform-{version}.tar.gz")
reproducible(archive)
print("Packaged", archive.name, "for platform", release["version"])
