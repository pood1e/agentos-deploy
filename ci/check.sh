#!/bin/sh
set -eu
ansible-lint
for playbook in install access connections deploy/validate; do
  ansible-playbook "playbooks/$playbook.yaml" --syntax-check
done
ansible-playbook ci/render-values.yaml
conftest verify --policy tests/policies
pin() {
  python -c "import sys, yaml; print(yaml.safe_load(open('playbooks/deploy/vars.yaml'))[sys.argv[1]])" "$1"
}
for scenario in .cache/check .cache/check/telemetry; do
  HELM_PLUGINS="$PWD/playbooks/deploy/helm-plugins" \
    AGENTOS_KUSTOMIZE_OVERLAY="$PWD/playbooks/deploy/kustomize/kagent" \
    AGENTOS_PATCHED_IMAGE="$(pin kagent_controller_image)" \
    helm template kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent --post-renderer agentos-kustomize \
    --version "$(pin kagent_version)" -f "$scenario/kagent-values.yaml" > "$scenario/native-kagent.yaml"
  conftest test --combine --policy tests/policies --namespace runtime_tests \
    --data .cache/check/test-data.json "$scenario/kagent-values.yaml" \
    .cache/check/substrate-values.yaml "$scenario/native-kagent.yaml"
done
python -m unittest discover -s tests
ruff check
ruff format --check
