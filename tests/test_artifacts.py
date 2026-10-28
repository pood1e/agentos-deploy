"""Exercise collection packaging and OCI verification against a disposable registry."""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class PackageTest(unittest.TestCase):
    def test_collection_pins_the_platform_release_and_repackages_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(
                ROOT,
                root,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".git", ".cache", "dist"),
            )
            values = root / "playbooks/charts/agentos/values.yaml"
            values.parent.mkdir(parents=True, exist_ok=True)
            values.write_text("harnesses: {}\n")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.test",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=root,
                check=True,
            )
            env = {key: value for key, value in os.environ.items() if not key.startswith("CI_")}
            env["AGENTOS_PLATFORM_REGISTRY"] = "registry.example.com/agentos"
            version = yaml.safe_load((root / "galaxy.yml").read_text())["version"]
            archive = root / f"dist/agentos-platform-{version}.tar.gz"
            digests = set()
            for _ in range(2):
                result = subprocess.run(
                    [sys.executable, "ci/package.py"],
                    cwd=root,
                    env=env,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                digests.add(hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(len(digests), 1)
            release = yaml.safe_load((root / "platform.yaml").read_text())
            with tarfile.open(archive) as collection:
                names = collection.getnames()
                manifest = json.load(collection.extractfile("FILES.json"))["files"]
                entries = [entry["name"] for entry in manifest]
                self.assertEqual(entries, sorted(entries, key=os.path.split))
                self.assertIn("playbooks/charts/agentos/values.yaml", names)
                self.assertFalse([name for name in names if name.split("/")[0] in ("ci", "tests")])
                for name in ("deploy", "environments"):
                    variables = yaml.safe_load(
                        collection.extractfile(f"playbooks/{name}/vars.yaml")
                    )
                    self.assertEqual(variables["delivery_version"], release["version"])
                    self.assertEqual(variables["delivery_revision"], release["revision"])
                    self.assertEqual(
                        variables["agentos_image_registry"], "registry.example.com/agentos"
                    )


class OCITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)
        with socket.socket() as port:
            port.bind(("127.0.0.1", 0))
            cls.registry = "127.0.0.1:" + str(port.getsockname()[1])
        cls.process = subprocess.Popen(
            ["crane", "registry", "serve", "--address", cls.registry],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                urllib.request.urlopen("http://" + cls.registry + "/v2/", timeout=1).close()
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError("Registry did not start")
        cls.env = {**os.environ, "COSIGN_PASSWORD": "test-only"}
        subprocess.run(
            ["cosign", "generate-key-pair", "--output-key-prefix", str(cls.root / "cosign")],
            env=cls.env,
            check=True,
            capture_output=True,
        )
        cls.version, cls.revision = "1.0.0", "a" * 40
        (cls.root / "artifact.txt").write_text("original")
        tagged = cls.registry + "/collection:1.0.0"
        cls.push(tagged)
        cls.digest = subprocess.check_output(
            ["oras", "resolve", "--plain-http", tagged], text=True
        ).strip()
        cls.reference = cls.registry + "/collection@" + cls.digest
        subprocess.run(
            [
                "cosign",
                "sign",
                "--yes",
                "--allow-http-registry",
                "--key",
                str(cls.root / "cosign.key"),
                "--signing-config",
                str(ROOT / "ci/signing-config.json"),
                "-a",
                "version=" + cls.version,
                "-a",
                "revision=" + cls.revision,
                cls.reference,
            ],
            env=cls.env,
            check=True,
            capture_output=True,
        )

    @classmethod
    def push(cls, tagged):
        subprocess.run(
            [
                "oras",
                "push",
                "--image-spec",
                "v1.0",
                "--plain-http",
                tagged,
                "artifact.txt:application/octet-stream",
            ],
            cwd=cls.root,
            check=True,
            capture_output=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.directory.cleanup()

    def verify(self, reference=None, version=None, revision=None):
        return subprocess.run(
            [
                "cosign",
                "verify",
                "--allow-http-registry",
                "--key",
                str(self.root / "cosign.pub"),
                "--insecure-ignore-tlog",
                "-a",
                "version=" + (version or self.version),
                "-a",
                "revision=" + (revision or self.revision),
                reference or self.reference,
            ],
            env=self.env,
            text=True,
            capture_output=True,
        )

    def test_clean_pull_and_repeat_convergence(self):
        self.assertEqual(self.verify().returncode, 0)
        for _ in range(2):
            with tempfile.TemporaryDirectory() as target:
                subprocess.run(
                    ["oras", "pull", "--plain-http", self.reference, "--output", target],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual((Path(target) / "artifact.txt").read_text(), "original")

    def test_wrong_version_and_revision_are_rejected(self):
        self.assertNotEqual(self.verify(version="2.0.0").returncode, 0)
        self.assertNotEqual(self.verify(revision="b" * 40).returncode, 0)

    def test_tampered_tag_cannot_reuse_the_old_signature(self):
        (self.root / "artifact.txt").write_text("tampered")
        tagged = self.registry + "/collection:tampered"
        self.push(tagged)
        changed = subprocess.check_output(
            ["oras", "resolve", "--plain-http", tagged], text=True
        ).strip()
        self.assertNotEqual(
            self.verify(reference=self.registry + "/collection@" + changed).returncode, 0
        )


if __name__ == "__main__":
    unittest.main()
