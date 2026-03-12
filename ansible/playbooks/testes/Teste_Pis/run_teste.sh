#!/bin/bash

# Script para executar stress teste CPU+GPU nas Raspberry Pis

INVENTORY="ansible/inventory"
ORQUESTRADOR="ansible/playbooks/testes/Teste_Pis/teste_stable_ORQUESTRADOR.yml"
PARAR="ansible/playbooks/testes/Teste_Pis/teste_stable_parar.yml"
VAULT_PASS="~/TESTBED-BKP/.ansible_vault_pass"

# Função que para os testes
parar_testes() {
    echo ""
    echo "=========================================="
    echo "  INTERROMPIDO! Parando testes..."
    echo "=========================================="
    cd ~/HIAAC-FL-Testbed
    ansible-playbook -i "$INVENTORY" "$PARAR" --vault-password-file "$VAULT_PASS"
    exit 1
}

# Capturar Ctrl+C e outros sinais de interrupção
trap parar_testes SIGINT SIGTERM

echo "=========================================="
echo "  Iniciando STRESS CPU+GPU nas Pis"
echo "  Os testes rodarão INDEFINIDAMENTE"
echo "  Pressione Ctrl+C para parar"
echo "=========================================="

cd ~/HIAAC-FL-Testbed
ansible-playbook -i "$INVENTORY" "$ORQUESTRADOR" --vault-password-file "$VAULT_PASS"

EXIT_CODE=$?

# Exit codes do Ansible:
# 0 = Success
# 2 = Failure
# 4 = Unreachable hosts (Pi offline, mas outras podem ter funcionado)
# 99+ = Interrupted (Ctrl+C)

# Só parar testes em caso de falha CRÍTICA (não-conectividade)
if [ $EXIT_CODE -eq 2 ] || [ $EXIT_CODE -ge 99 ]; then
    echo ""
    echo "=========================================="
    echo "   Playbook interrompido (código: $EXIT_CODE)"
    echo "  Executando limpeza..."
    echo "=========================================="
    ansible-playbook -i "$INVENTORY" "$PARAR" --vault-password-file "$VAULT_PASS"
    exit $EXIT_CODE
fi

# Se exit code 4 (unreachable), apenas avisar mas NÃO parar
if [ $EXIT_CODE -eq 4 ]; then
    echo ""
    echo "=========================================="
    echo "   Algumas Pis offline, mas testes iniciados"
    echo "  Verifique quais Pis responderam acima"
    echo "=========================================="
    exit 0
fi

echo ""
echo "=========================================="
echo "  Testes iniciados!"
echo "  Rodando em background nas Pis"
echo "  Use ansible-playbook -i ansible/inventory ansible/playbooks/testes/Teste_Pis/teste_stable_parar.yml --vault-password-file ~/TESTBED-BKP/.ansible_vault_pass para parar"
echo "=========================================="
