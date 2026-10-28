package runtime_tests

import rego.v1

deny contains "native controller must verify OIDC identity" if not native_authentication

native_authentication if {
	native_config.server.auth == kagent.config.server.auth
	native_config.server.auth.mode == "oidc"
	startswith(native_config.server.auth.oidc.issuer, "https://")
	native_config.server.auth.oidc.audience != ""
}

deny contains "native execution authority differs from site policy" if not native_authority

native_authority if {
	authority := native_config.executionAuthorization
	authority == kagent.config.executionAuthorization
	authority.scopeClaim != ""
	is_array(authority.gatewayAudiences)
	count(authority.gatewayAudiences) > 0
	count(authority.rules) > 0
	authority.encryptionKeyFile == "/etc/kagent/execution/key"
	startswith(authority.oauth.tokenEndpoint, "https://")
	authority.oauth.clientId != ""
	authority.oauth.clientSecretFile == "/etc/kagent/identity/client-secret"
}

deny contains "native execution key must be controller-only" if not native_execution_key_volume

native_execution_key_volume if {
	volume := native_controller.spec.template.spec.volumes[_]
	volume.name == "execution-credentials"
	volume.secret == {"secretName": "kagent-execution-credentials", "defaultMode": 288}
	container := native_controller.spec.template.spec.containers[_]
	container.name == "controller"
	container.volumeMounts[_] == {"name": "execution-credentials", "mountPath": "/etc/kagent/execution", "readOnly": true}
	native_controller.spec.template.spec.securityContext.fsGroup == 65532
}

deny contains "native identity renewal requires a mounted client Secret" if not native_identity_volume

native_identity_volume if {
	volume := native_controller.spec.template.spec.volumes[_]
	volume.name == "identity-client"
	volume.secret.defaultMode == 288
	volume.secret.items == [{"key": "client-secret", "path": "client-secret"}]
	container := native_controller.spec.template.spec.containers[_]
	container.name == "controller"
	container.volumeMounts[_] == {"name": "identity-client", "mountPath": "/etc/kagent/identity", "readOnly": true}
}

deny contains "native discovery must use the invocation audience" if not native_discovery_volume

native_discovery_volume if {
	volume := native_controller.spec.template.spec.volumes[_]
	volume.name == "mcp-discovery"
	volume.projected.sources == [{"serviceAccountToken": {"path": "token", "audience": "kagent-invocation", "expirationSeconds": 3600}}]
	native_config.server.auth.serviceAccount.authority == "kubernetes"
}
