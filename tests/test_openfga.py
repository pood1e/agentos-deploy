"""Validate the rendered OpenFGA deployment boundary."""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class OpenFGADeploymentTest(unittest.TestCase):
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
        credentials = {env["name"]: env for env in server["env"]}
        self.assertEqual(
            credentials["OPENFGA_AUTHN_PRESHARED_KEYS"]["valueFrom"]["secretKeyRef"],
            {"name": "openfga-auth", "key": "keys"},
        )
        self.assertEqual(credentials["OPENFGA_HTTP_TLS_ENABLED"]["value"], "true")
