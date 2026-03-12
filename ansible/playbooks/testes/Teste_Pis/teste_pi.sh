#!/bin/bash

# Instalação de dependências
sudo apt update
sudo apt install stress-ng -y

# Função de cleanup para Ctrl+C
cleanup() {
    echo -e "\nParando stress teste..."
    pkill -f stress-ng
    exit 0
}
trap cleanup SIGINT SIGTERM

# Inicia stress COMPLETO (indefinido)
echo "Iniciando STRESS CPU + GPU + RAM (indefinido)"

# CPU: 100% de todos os cores
stress-ng --cpu 0 \
          --vm 2 --vm-bytes 75% \
          --timeout 0 &

# Stress GPU via renderização 3D (funciona headless na Pi 5)
# Usa /dev/dri diretamente se disponível
if [ -e /dev/dri/card0 ]; then
    echo "GPU detectada, iniciando stress GPU..."
    # Tenta glmark2-es2-drm (versão headless)
    if command -v glmark2-es2-drm &> /dev/null; then
        while true; do
            glmark2-es2-drm --off-screen 2>/dev/null || sleep 1
        done &
    else
        echo "glmark2-es2-drm não disponível, apenas CPU+RAM"
    fi
else
    echo "GPU não detectada, apenas CPU+RAM"
fi

echo "Stress iniciado! Pressione Ctrl+C para parar"
echo "   Ou use: pkill -f stress-ng"

# Mantém script rodando (senão sai imediatamente)
wait