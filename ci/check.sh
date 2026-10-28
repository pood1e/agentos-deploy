#!/bin/sh
set -eu
ansible-lint
for playbook in install access connections deploy/validate; do
  ansible-playbook "playbooks/$playbook.yaml" --syntax-check
done
ansible-playbook ci/render-values.yaml
conftest verify --policy tests/policies
HELM_PLUGINS="$PWD/playbooks/deploy/helm-plugins" \
  AGENTOS_KUSTOMIZE_OVERLAY="$PWD/playbooks/deploy/kustomize/substrate" \
  AGENTOS_PATCHED_IMAGE="$(python -c 'import yaml; print(yaml.safe_load(open("playbooks/deploy/vars.yaml"))["substrate_api_image"])')" \
  helm template substrate oci://ghcr.io/kagent-dev/substrate/helm/substrate \
  --version "$(python -c 'import yaml; print(yaml.safe_load(open("playbooks/deploy/vars.yaml"))["substrate_version"])')" \
  --post-renderer agentos-kustomize --namespace ate-system \
  -f .cache/check/substrate-values.yaml > .cache/check/native-substrate.yaml
pin() {
  python -c "import sys, yaml; print(yaml.safe_load(open('playbooks/deploy/vars.yaml'))[sys.argv[1]])" "$1"
}
for scenario in .cache/check .cache/check/telemetry .cache/check/private-identity; do
  HELM_PLUGINS="$PWD/playbooks/deploy/helm-plugins" \
    AGENTOS_KUSTOMIZE_OVERLAY="$PWD/playbooks/deploy/kustomize/kagent" \
    AGENTOS_PATCHED_IMAGE="$(pin kagent_controller_image)" \
    helm template kagent ".cache/check/runtime/kagent-$(pin kagent_runtime_version).tgz" --post-renderer agentos-kustomize \
    --namespace agentos -f "$scenario/kagent-values.yaml" > "$scenario/native-kagent.yaml"
  conftest test --combine --policy tests/policies --namespace runtime_tests \
    --data .cache/check/test-data.json "$scenario/kagent-values.yaml" \
    .cache/check/substrate-values.yaml "$scenario/native-kagent.yaml" .cache/check/runtime-ingress.yaml
done
python -m unittest discover -s tests
ruff check
ruff format --check
