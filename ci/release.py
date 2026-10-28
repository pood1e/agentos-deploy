"""Collection release identity, pinned platform release and reproducible archives."""

import gzip
import io
import os
import subprocess
import tarfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLATFORM_KEY = ROOT / "playbooks/deploy/files/cosign.pub"
COLLECTION_KEY = ROOT / "ci/cosign.pub"
SOURCE = "https://github.com/pood1e/agentos-deploy.git"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def identity():
    """Return the collection version and the source revision of this checkout."""
    revision = git("rev-parse", "HEAD")
    if os.environ.get("CI_COMMIT_SHA", revision) != revision:
        raise ValueError("Pipeline and checkout revisions differ")
    version = yaml.safe_load((ROOT / "galaxy.yml").read_text())["version"]
    tag = os.environ.get("CI_COMMIT_TAG", "")
    if tag:
        if tag != f"v{version}":
            raise ValueError("Release tag and collection version differ")
        refs = dict(
            line.split()[::-1]
            for line in git(
                "ls-remote", SOURCE, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"
            ).splitlines()
        )
        if refs.get(f"refs/tags/{tag}^{{}}", refs.get(f"refs/tags/{tag}")) != revision:
            raise ValueError("Source and build release tag revisions differ")
    return version, revision


def platform():
    """Return the pinned platform release and the registry the build environment provides."""
    release = yaml.safe_load((ROOT / "platform.yaml").read_text())
    release["registry"] = os.environ["AGENTOS_PLATFORM_REGISTRY"]
    return release


def reproducible(archive):
    epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    with tarfile.open(archive) as original:
        members = [
            (item, original.extractfile(item).read() if item.isfile() else None)
            for item in original.getmembers()
        ]
    with (
        archive.open("wb") as output,
        gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=epoch) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as packed,
    ):
        for item, content in sorted(members, key=lambda member: member[0].name):
            item.mtime, item.uid, item.gid, item.uname, item.gname = epoch, 0, 0, "", ""
            item.pax_headers = {}
            packed.addfile(item, io.BytesIO(content) if content is not None else None)
