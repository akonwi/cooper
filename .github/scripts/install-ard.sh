#!/usr/bin/env bash
set -euo pipefail

version="${1:?Ard release version required}"
destination="${2:?Installation directory required}"
[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
case "$(uname -s)" in
  Linux) os=linux ;;
  Darwin) os=darwin ;;
  *) echo 'Unsupported Ard operating system' >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) echo 'Unsupported Ard architecture' >&2; exit 1 ;;
esac

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
archive="ard_${version}_${os}_${arch}.tar.gz"
release="https://github.com/akonwi/ard/releases/download/$version"
curl -fsSL --retry 3 "$release/$archive" -o "$scratch/$archive"
curl -fsSL --retry 3 "$release/checksums.txt" -o "$scratch/checksums.txt"
checksum="$(awk -v archive="$archive" '$2 == "dist/" archive { print $1 }' "$scratch/checksums.txt")"
[[ "$checksum" =~ ^[0-9a-f]{64}$ ]]
(
  cd "$scratch"
  if command -v sha256sum >/dev/null; then
    printf '%s  %s\n' "$checksum" "$archive" | sha256sum -c -
  else
    printf '%s  %s\n' "$checksum" "$archive" | shasum -a 256 -c -
  fi
)
tar -xzf "$scratch/$archive" -C "$scratch" ard
mkdir -p "$destination"
install -m 755 "$scratch/ard" "$destination/ard"
"$destination/ard" version
