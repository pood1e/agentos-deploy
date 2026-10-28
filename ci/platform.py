"""Verify the pinned platform chart and extract the defaults the playbooks read."""

import subprocess
import tarfile
import tempfile
from pathlib import Path

import yaml
from release import PLATFORM_KEY, ROOT, platform

release = platform()
repository = release["registry"] + "/charts/agentos"
digest = subprocess.check_output(
    ["oras", "resolve", repository + ":" + release["version"]], text=True
).strip()
subprocess.run(
    [
        "cosign",
        "verify",
        "--key",
        str(PLATFORM_KEY),
        "--insecure-ignore-tlog",
        "-a",
        "version=" + release["version"],
        "-a",
        "revision=" + release["revision"],
        repository + "@" + digest,
    ],
    check=True,
    stdout=subprocess.DEVNULL,
)
with tempfile.TemporaryDirectory() as directory:
    subprocess.run(
        ["helm", "pull", "oci://" + repository + "@" + digest, "--destination", directory],
        check=True,
        capture_output=True,
    )
    (archive,) = Path(directory).glob("*.tgz")
    with tarfile.open(archive) as chart:
        metadata = yaml.safe_load(chart.extractfile("agentos/Chart.yaml"))
        values = chart.extractfile("agentos/values.yaml").read()
if (
    metadata["version"] != release["version"]
    or metadata["annotations"]["org.opencontainers.image.revision"] != release["revision"]
):
    raise ValueError("Platform chart identity differs from platform.yaml")
target = ROOT / "playbooks/charts/agentos/values.yaml"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(values)
print("Verified platform", release["version"], repository + "@" + digest)
