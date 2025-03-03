#!/bin/bash

set -e

GITHUB_USER="yourusername"
GITHUB_REPO="localforward"
LATEST_RELEASE=$(curl -s https://api.github.com/repos/$GITHUB_USER/$GITHUB_REPO/releases/latest | grep "browser_download_url" | cut -d '"' -f 4)

if [[ -z "$LATEST_RELEASE" ]]; then
    echo "Failed to find the latest release. Check your GitHub repo."
    exit 1
fi

INSTALL_DIR="/usr/local/bin"
BIN_NAME="localforward"

echo "Downloading localforward..."
curl -L $LATEST_RELEASE -o /tmp/$BIN_NAME

echo "Setting executable permissions..."
chmod +x /tmp/$BIN_NAME

echo "Moving to $INSTALL_DIR..."
sudo mv /tmp/$BIN_NAME $INSTALL_DIR/$BIN_NAME

echo "Installation complete! Run 'localforward --help' to get started."
