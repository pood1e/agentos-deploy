#!/bin/sh
set -eu
umask 077
context=.cache/ci-tools-image
image=$CI_REGISTRY_IMAGE/ci/tools
mkdir -p "$context/ci"
tar -cf - mise.toml mise.lock requirements.txt ci/requirements.txt ci/collections.yaml | tar -xf - -C "$context"
export DOCKER_CONFIG="$CI_PROJECT_DIR/.cache/build-auth"
mkdir -p "$DOCKER_CONFIG"
auth=$(printf '%s:%s' "$CI_REGISTRY_USER" "$CI_REGISTRY_PASSWORD" | base64 | tr -d '\n')
printf '{"auths":{"%s":{"auth":"%s"}}}\n' "$CI_REGISTRY" "$auth" > "$DOCKER_CONFIG/config.json"
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
BUILDKITD_FLAGS=--oci-worker-no-process-sandbox
if [ -n "${AGENTOS_REGISTRY_MIRROR:-}" ]; then
  printf '[registry."docker.io"]\n  mirrors = ["%s"]\n' "$AGENTOS_REGISTRY_MIRROR" > .cache/buildkit.toml
  BUILDKITD_FLAGS="$BUILDKITD_FLAGS --config $CI_PROJECT_DIR/.cache/buildkit.toml"
fi
export BUILDKITD_FLAGS
buildctl-daemonless.sh build \
  --frontend dockerfile.v0 \
  --local context="$context" --local dockerfile=ci/images \
  --opt platform=linux/amd64 \
  --opt "label:org.opencontainers.image.revision=$CI_COMMIT_SHA" \
  --opt "label:org.opencontainers.image.source=$CI_PROJECT_URL" \
  --import-cache "type=registry,ref=$image:buildcache" \
  --export-cache "type=registry,ref=$image:buildcache,mode=max" \
  --output "type=image,name=$image:$CI_COMMIT_SHA,push=true" \
  --metadata-file .cache/ci-tools.json
digest=$(sed -n 's/.*"containerimage.digest": *"\([^"]*\)".*/\1/p' .cache/ci-tools.json)
echo "CI tools image: $image@$digest"
