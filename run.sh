#!/bin/bash

# Sobe o servidor FL e os clientes via ansible, captura o tráfego de rede e copia os logs no final

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
INVENTORY_PATH="${HIAAC_INVENTORY:-$ROOT_DIR/ansible/inventory}"
VAULT_PASS="${HIAAC_VAULT_PASS:-$HOME/.ansible_vault_pass}"
PYTHON_VERSION="${HIAAC_PYTHON_VERSION:-python3.10}"
LOGS_DIR="${HIAAC_LOGS_DIR:-$HOME/app/logs}"
FLOWER_PORT="${HIAAC_FLOWER_PORT:-8080}"
SERVER_PROCESS="${HIAAC_SERVER_PROCESS:-server.py}"

# Resolve o IP do controller na interface que alcança os clientes (clientes que
# leiam HIAAC_SERVER_ADDRESS pegam esse valor; os modelos de exemplo embutem o IP)
if [ -z "$HIAAC_SERVER_ADDRESS" ]; then
    CONTROLLER_IP=$(ip route get 10.10.10.1 2>/dev/null | awk '/src/{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1);exit}}')
    [ -z "$CONTROLLER_IP" ] && CONTROLLER_IP=$(hostname -I | awk '{print $1}')
    export HIAAC_SERVER_ADDRESS="${CONTROLLER_IP}:${FLOWER_PORT}"
    echo "Server address: $HIAAC_SERVER_ADDRESS"
fi

# Garantir que não há processos de experimentos anteriores
echo "Parando processos de experimentos anteriores..."
./force_stop.sh > /dev/null 2>&1
sleep 5

# Limpar logs antigos do servidor
echo "Limpando logs antigos do servidor..."
rm -rf "$LOGS_DIR"/client-* 2>/dev/null

# Limpar pcaps antigos (manter só últimos 3 para debug)
echo "Limpando pcaps antigos..."
mkdir -p "$LOGS_DIR/pcaps"
ls -t "$LOGS_DIR/pcaps"/*.pcap 2>/dev/null | tail -n +4 | xargs -r rm -f

# Limpar logs antigos dos dispositivos para começar limpo
echo "Limpando logs antigos dos dispositivos..."
ansible-playbook -i "$INVENTORY_PATH" ansible/playbooks/utils/clean_all_logs.yaml --vault-password-file "$VAULT_PASS" > /dev/null 2>&1
echo "Iniciando novo experimento..."

ansible-playbook -i "$INVENTORY_PATH" ansible/playbooks/deploy/start_server.yaml --vault-password-file "$VAULT_PASS" -e "PYTHON_VERSION=$PYTHON_VERSION client_args=$ARGS" > server-app.log 2>&1 &
SERVER_PID=$!

sleep 20

TIMESTAMP="$(date +'%H:%M:%d-%m-%Y')"
FILENAME="${LOGS_DIR}/pcaps/${TIMESTAMP}.pcap"
mkdir -p "$LOGS_DIR/pcaps"
sudo tcpdump -i any -nn -w "$FILENAME" "port $FLOWER_PORT" &
TCPDUMP_PID=$!

ansible-playbook -i "$INVENTORY_PATH" ansible/playbooks/deploy/start_clients.yaml --vault-password-file "$VAULT_PASS" -e "PYTHON_VERSION=$PYTHON_VERSION" > client.log 2>&1 &
CLIENT_PID=$!

# Aguardar o treinamento terminar monitorando os processos ativos
echo "Aguardando conclusão do treinamento federado..."
echo "Capturando tráfego de rede em ${FILENAME}"

# Esperar um pouco para os processos iniciarem
sleep 30

# Monitorar enquanto houver processos de servidor rodando
while pgrep -f "$SERVER_PROCESS" > /dev/null; do
    sleep 10
done

# Aguardar mais um pouco para garantir captura completa
echo "Servidor finalizado, aguardando 15s para finalizar captura..."
sleep 15

# Para o tcpdump
sudo pkill -x tcpdump 2>/dev/null || true
echo "Captura de rede finalizada: ${FILENAME}"

ansible-playbook -i "$INVENTORY_PATH" ansible/playbooks/after_run/copy_to_server.yaml --vault-password-file "$VAULT_PASS" -e "PYTHON_VERSION=$PYTHON_VERSION" > save_client_data.log 2>&1