#!/usr/bin/env bash
#
# Sims Forever Tracker — macOS installer
#
#   curl -fsSL https://raw.githubusercontent.com/USER/REPO/main/install.sh | bash
#
# Downloads the latest release and installs it to /Applications.
#
# Why this avoids the "Apple could not verify..." warning: the quarantine
# flag that triggers Gatekeeper is applied by web browsers, not by macOS
# itself. Files fetched with curl never get it. This is the same mechanism
# Homebrew relies on — it isn't a security bypass, it's you choosing to run
# an install command instead of clicking a download link.
#
# The app is unsigned because code signing requires a paid Apple Developer
# account. Read this script before running it, as you should with any
# install script.

set -euo pipefail

REPO="USER/REPO"                      # <-- set to your GitHub user/repo
ASSET="SimsTracker-macos.zip"
APP="SimsTracker.app"
DEST="/Applications"

info()  { printf '\033[36m%s\033[0m\n' "$1"; }
ok()    { printf '\033[32m%s\033[0m\n' "$1"; }
fail()  { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || fail "This installer is for macOS only."

URL="https://github.com/${REPO}/releases/latest/download/${ASSET}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

info "Downloading the latest release..."
curl -fsSL "$URL" -o "$TMP/$ASSET" \
  || fail "Download failed. Check that a release exists at: $URL"

info "Unpacking..."
ditto -x -k "$TMP/$ASSET" "$TMP/unpacked" \
  || fail "Could not unpack $ASSET."

[ -d "$TMP/unpacked/$APP" ] || fail "$APP was not in the archive."

if [ -d "$DEST/$APP" ]; then
    info "Replacing the existing installation..."
    # Your sessions and Sims live in ~/Library/Application Support, not in
    # the app, so replacing the app never touches your data.
    rm -rf "${DEST:?}/$APP"
fi

info "Installing to $DEST..."
if ! ditto "$TMP/unpacked/$APP" "$DEST/$APP" 2>/dev/null; then
    info "Needs permission to write to $DEST — you may be asked for your password."
    sudo ditto "$TMP/unpacked/$APP" "$DEST/$APP" \
      || fail "Could not install to $DEST."
fi

# Belt and braces: clear quarantine if anything set it. -r is required
# because an .app is a directory and every file inside carries the flag.
xattr -dr com.apple.quarantine "$DEST/$APP" 2>/dev/null || true

ok "Installed: $DEST/$APP"
echo
echo "Open it from Applications or Spotlight."
echo "Your data lives in ~/Library/Application Support/SimsForeverTracker/"
