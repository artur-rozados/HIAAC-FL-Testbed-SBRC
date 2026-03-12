#!/bin/bash

# Sobe o servidor FL e os clientes via ansible, captura o tráfego de rede e copia os logs no final

# Garantir que não há processos de experimentos anteriores
echo "Parando processos de experimentos anteriores..."
./force_stop.sh > /dev/null 2>&1
sleep 5

# Limpar logs antigos do servidor
echo "Limpando logs antigos do servidor..."
rm -rf ~/app/logs/client-* 2>/dev/null

# Limpar pcaps antigos (manter só últimos 3 para debug)
echo "Limpando pcaps antigos..."
mkdir -p ~/app/logs/pcaps
ls -t ~/app/logs/pcaps/*.pcap 2>/dev/null | tail -n +4 | xargs -r rm -f

# Limpar logs antigos dos dispositivos para começar limpo
echo "Limpando logs antigos dos dispositivos..."
ansible-playbook -i ansible/inventory ansible/playbooks/utils/clean_all_logs.yaml --vault-password-file ~/.ansible_vault_pass > /dev/null 2>&1
echo "Iniciando novo experimento..."

ansible-playbook -i ansible/inventory ansible/playbooks/deploy/start_server.yaml --vault-password-file ~/.ansible_vault_pass -e "PYTHON_VERSION=python3.11 client_args=$ARGS" > server-app.log &
SERVER_PID=$!

sleep 20

TIMESTAMP="$(date +'%H:%M:%d-%m-%Y')"
FILENAME="${HOME}/app/logs/pcaps/${TIMESTAMP}.pcap"
mkdir -p ~/app/logs/pcaps
sudo tcpdump -i any -nn -w "$FILENAME" 'port 8080' &
TCPDUMP_PID=$!

ansible-playbook -i ansible/inventory ansible/playbooks/deploy/start_clients.yaml --vault-password-file ~/.ansible_vault_pass -e "PYTHON_VERSION=python3.11" > client.log &
CLIENT_PID=$!

# Aguardar o treinamento terminar monitorando os processos ativos
echo "Aguardando conclusão do treinamento federado..."
echo "Capturando tráfego de rede em ${FILENAME}"

# Esperar um pouco para os processos iniciarem
sleep 30

# Monitorar enquanto houver processos de servidor rodando
while pgrep -f "server.py" > /dev/null; do
    sleep 10
done

# Aguardar mais um pouco para garantir captura completa
echo "Servidor finalizado, aguardando 15s para finalizar captura..."
sleep 15

# Para o tcpdump
sudo pkill -x tcpdump 2>/dev/null || true
echo "Captura de rede finalizada: ${FILENAME}"

ansible-playbook -i ansible/inventory ansible/playbooks/after_run/copy_to_server.yaml --vault-password-file ~/.ansible_vault_pass -e "PYTHON_VERSION=python3.11" > save_client_data.log