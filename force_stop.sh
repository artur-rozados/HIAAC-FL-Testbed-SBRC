#!/bin/bash

pkill -f "tcpdump"

echo "Stop clients"
ansible-playbook -i ansible/inventory ansible/playbooks/stop/stop_flower_clients.yaml --vault-password-file ~/.ansible_vault_pass -e "PYTHON_VERSION=python3.11" > stop_client.log &

echo "Stop server"
pkill -f "server.py"

