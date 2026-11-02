"""Validate the rendered OpenFGA deployment boundary."""

import base64
import json
import tarfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class OpenFGADeploymentTest(unittest.TestCase):
    def test_packaged_model_bootstraps_exact_workspace_identities(self):
        version = yaml.safe_load((ROOT / "playbooks/deploy/vars.yaml").read_text())[
            "kagent_runtime_version"
        ]
        chart = ROOT / f".cache/check/runtime/kagent-{version}.tgz"
        with tarfile.open(chart, "r:gz") as archive:
            model = json.load(archive.extractfile("kagent/files/authorization-model.json"))
        workspace = next(item for item in model["type_definitions"] if item["type"] == "workspace")
        roles = {
            "member",
            "access_admin",
            "definition_reader",
            "definition_editor",
            "workflow_editor",
            "workflow_publisher",
            "executor",
            "auditor",
            "operator",
            "dependency_reader",
            "dependency_user",
            "dependency_manager",
        } & workspace["relations"].keys()

        def encode(value):
            return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")

        principal = encode("oidc:https://identity.example.test") + "." + encode("alice")
        user = "principal:" + encode(principal)
        tuples = json.loads((ROOT / ".cache/check/openfga-bootstrap-tuples.json").read_text())
        expected = {
            (user, role, f"workspace:{uid}")
            for uid in ("workspace-agentos", "workspace-team-a")
            for role in roles
        }
        self.assertEqual(
            {(item["user"], item["relation"], item["object"]) for item in tuples},
            expected,
        )
        self.assertEqual(len(tuples), len(expected))

    def test_chart_uses_isolated_postgres_authenticated_tls_and_pinned_images(self):
        values = yaml.safe_load((ROOT / ".cache/check/openfga-values.yaml").read_text())
        manifests = {
            item["kind"]: item
            for item in yaml.safe_load_all((ROOT / ".cache/check/native-openfga.yaml").read_text())
            if item
        }
        deployment = manifests["Deployment"]["spec"]["template"]["spec"]
        server = deployment["containers"][0]
        migration = manifests["Job"]["spec"]["template"]["spec"]["containers"][0]

        self.assertEqual(values["datastore"]["engine"], "postgres")
        self.assertEqual(values["datastore"]["uriSecret"], "openfga-postgres")
        self.assertEqual(
            values["authn"], {"method": "preshared", "preshared": {"keysSecret": "openfga-auth"}}
        )
        self.assertTrue(values["http"]["tls"]["enabled"])
        self.assertFalse(values["playground"]["enabled"])
        self.assertIn("@sha256:", server["image"])
        self.assertEqual(server["image"], migration["image"])
        self.assertIn("@sha256:", deployment["initContainers"][0]["image"])
        self.assertIn(
            {"name": "tls", "secret": {"secretName": "openfga-tls"}}, deployment["volumes"]
        )
        self.assertIn(
            {"name": "tls", "mountPath": "/etc/openfga/tls", "readOnly": True},
            server["volumeMounts"],
        )
        self.assertIn(
            {"name": "postgres-ca", "mountPath": "/etc/openfga/postgres", "readOnly": True},
            server["volumeMounts"],
        )
        self.assertIn(
            {"name": "postgres-ca", "mountPath": "/etc/openfga/postgres", "readOnly": True},
            migration["volumeMounts"],
        )
        ca_volume = {
            "name": "postgres-ca",
            "secret": {
                "secretName": "kagent-postgres-ca",
                "items": [{"key": "ca.crt", "path": "ca.crt"}],
            },
        }
        self.assertIn(ca_volume, deployment["volumes"])
        self.assertIn(ca_volume, manifests["Job"]["spec"]["template"]["spec"]["volumes"])
        credentials = {env["name"]: env for env in server["env"]}
        self.assertEqual(
            credentials["OPENFGA_AUTHN_PRESHARED_KEYS"]["valueFrom"]["secretKeyRef"],
            {"name": "openfga-auth", "key": "keys"},
        )
        self.assertEqual(credentials["OPENFGA_HTTP_TLS_ENABLED"]["value"], "true")
