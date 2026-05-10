#!/bin/bash

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
INVENTORY_PATH="${HIAAC_INVENTORY:-$ROOT_DIR/ansible/inventory}"
VAULT_PASS="${HIAAC_VAULT_PASS:-$HOME/.ansible_vault_pass}"
PYTHON_VERSION="${HIAAC_PYTHON_VERSION:-python3.11}"
SERVER_PROCESS="${HIAAC_SERVER_PROCESS:-server.py}"

pkill -f "tcpdump"

echo "Stop clients"
ansible-playbook -i "$INVENTORY_PATH" ansible/playbooks/stop/stop_flower_clients.yaml --vault-password-file "$VAULT_PASS" -e "PYTHON_VERSION=$PYTHON_VERSION" > stop_client.log &

echo "Stop server"
pkill -f "$SERVER_PROCESS"

