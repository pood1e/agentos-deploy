FROM ghcr.io/jdx/mise:2026.10.18@sha256:fc31de7b93d195613deb600d42c65a164b0205716ade38132aadeabac3838248 AS mise
FROM ubuntu:24.04@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git openssh-client \
    && rm -rf /var/lib/apt/lists/*
COPY --from=mise /usr/local/bin/mise /usr/local/bin/mise
ENV MISE_DATA_DIR=/opt/mise MISE_CACHE_DIR=/tmp/mise-cache \
    MISE_GLOBAL_CONFIG_FILE=/opt/agentos-deploy/mise.toml \
    MISE_TRUSTED_CONFIG_PATHS=/opt/agentos-deploy:/builds \
    ANSIBLE_COLLECTIONS_PATH=/opt/agentos-deploy/collections \
    PATH=/opt/agentos-deploy/venv/bin:/opt/mise/shims:$PATH
WORKDIR /opt/agentos-deploy
COPY mise.toml mise.lock ./
RUN mise install --locked && mise reshim && rm -rf /tmp/mise-cache
COPY requirements.txt ./
COPY ci/ ci/
RUN uv venv venv --python "$(mise which python)" \
    && uv pip install --python venv/bin/python -r requirements.txt -r ci/requirements.txt \
    && ansible-galaxy collection install -r ci/collections.yaml -p collections \
    && uv cache clean
WORKDIR /builds
