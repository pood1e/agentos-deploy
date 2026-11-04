# Sourced by CI jobs: the mise.lock toolchain, a job-local Python environment and
# job-local registry credentials.
mise install --locked
eval "$(mise env --shell bash)"
uv venv --quiet --clear --python "$(mise which python)" .cache/venv
uv pip install --quiet --python .cache/venv/bin/python -r requirements.txt -r ci/requirements.txt
export PATH="$CI_PROJECT_DIR/.cache/venv/bin:$PATH"
export DOCKER_CONFIG="$CI_PROJECT_DIR/.cache/registry"
export HELM_REGISTRY_CONFIG="$DOCKER_CONFIG/helm.json"
