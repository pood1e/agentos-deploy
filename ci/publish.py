"""Publish the verified collection archive and sign its immutable digest."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from release import COLLECTION_KEY, ROOT, identity

version, revision = identity()
archive = ROOT / f"dist/agentos-platform-{version}.tar.gz"
repository = os.environ["CI_REGISTRY_IMAGE"] + "/collections/platform"
tagged = repository + ":" + version


def descriptor(reference):
    result = subprocess.run(
        ["oras", "manifest", "fetch", "--descriptor", reference], text=True, capture_output=True
    )
    if result.returncode == 0:
        return json.loads(result.stdout)["digest"]
    if any(marker in result.stderr.lower() for marker in ("not found", "manifest_unknown", "404")):
        return None
    raise RuntimeError(result.stderr)


def cosign(*args):
    subprocess.run(
        [
            "cosign",
            *args,
            "-a",
            "version=" + version,
            "-a",
            "revision=" + revision,
            repository + "@" + digest,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


subprocess.run(
    [
        "oras",
        "login",
        os.environ["CI_REGISTRY"],
        "--username",
        os.environ["CI_REGISTRY_USER"],
        "--password-stdin",
    ],
    input=os.environ["CI_REGISTRY_PASSWORD"],
    text=True,
    check=True,
    capture_output=True,
)
digest = descriptor(tagged)
if digest:
    with tempfile.TemporaryDirectory() as target:
        subprocess.run(["oras", "pull", repository + "@" + digest, "--output", target], check=True)
        if Path(target, archive.name).read_bytes() != archive.read_bytes():
            raise ValueError("Published collection differs")
else:
    subprocess.run(
        [
            "oras",
            "push",
            "--image-spec",
            "v1.0",
            "--annotation",
            "org.opencontainers.image.version=" + version,
            "--annotation",
            "org.opencontainers.image.revision=" + revision,
            tagged,
            archive.name + ":application/gzip",
        ],
        cwd=archive.parent,
        check=True,
    )
    digest = descriptor(tagged)
cosign(
    "sign",
    "--yes",
    "--key",
    os.environ["COSIGN_PRIVATE_KEY"],
    "--signing-config",
    str(ROOT / "ci/signing-config.json"),
)
cosign("verify", "--key", str(COLLECTION_KEY), "--insecure-ignore-tlog")
print("Published", repository + "@" + digest)
