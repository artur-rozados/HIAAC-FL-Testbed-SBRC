# HIAAC-FL-Testbed



<p align="center">
  <img src="https://img.shields.io/badge/Ansible-EE0000?logo=ansible&logoColor=white" alt="Ansible">
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Raspberry%20Pi-A22846?logo=raspberrypi&logoColor=white" alt="Raspberry Pi">
  <img src="https://img.shields.io/badge/NVIDIA%20Jetson-76B900?logo=nvidia&logoColor=white" alt="NVIDIA Jetson">
  <img src="https://img.shields.io/badge/Telemetria-tcpdump-red" alt="Telemetria">
</p>

Testbed para experimentos de **Aprendizagem Federada (FL)** em hardware heterogêneo real. Orquestra automaticamente um cluster de mini-computadores (Raspberry Pi e NVIDIA Jetson) via Ansible, com interface gráfica Streamlit e monitoramento de hardware em tempo real.

> **Demo rápido (sem hardware):** veja a seção [▶ Exemplo Mínimo (Docker)](#-exemplo-mínimo-docker) para rodar um experimento FL local em segundos.

---

## 🏗️ Arquitetura do Ambiente

O testbed é composto por três tipos de nós em rede isolada:

| Nó | Quantidade | Papel |
|----|-----------|-------|
| **Servidor central** | 1 | Hospeda a GUI Streamlit, roda o servidor Flower e agrega logs |
| **Raspberry Pi 5** | 9 | Clientes FL — treinamento local com CPU ARM |
| **NVIDIA Jetson Orin Nano** | 6 | Clientes FL — treinamento com GPU integrada |

A comunicação entre servidor e clientes durante o treinamento usa o framework [Flower (flwr)](https://flower.ai/) v1.9.0 na porta 8080, com estratégia FedAvg.

Para usar o testbed com sua própria infraestrutura, copie `ansible/inventory.example` para `ansible/inventory` e edite com seus IPs e credenciais.

---

## ▶ Exemplo Mínimo (Docker)

Roda um experimento FL completo (1 servidor + 2 clientes, 3 rounds, dataset MNIST) **sem necessidade de hardware físico**, usando apenas Docker:

```bash
cd demo/
docker compose up --build
```

Veja [demo/README.md](demo/README.md) para detalhes e customização.

---

## 🕹️ Execução de Experimentos (testbed físico)

A execução é feita pela interface Streamlit, que centraliza o ciclo de vida completo de um experimento — do upload do modelo até o download dos resultados. Para um passo-a-passo visual com screenshots, veja o [Guia_de_uso.md](Guia_de_uso.md).

### Preparação do modelo

O modelo deve ser empacotado em um `.zip` com a seguinte estrutura:

```
modelo.zip
├── client.py        # lógica do cliente Flower (treinamento local, métricas)
├── server.py        # lógica do servidor Flower (estratégia, número de rounds, etc.)
└── requirements.txt # dependências Python do modelo
```

Há três modelos de exemplo prontos em `MODELOS_exemplos/Modelos/`, em variantes de complexidade crescente (`light`, `medium` e `heavy`), úteis para validar o ambiente ou servir de base para novos modelos.

### Fluxo do experimento

**1. Deploy** — Antes de rodar, os arquivos do modelo precisam ser distribuídos para todos os dispositivos. Pelo Streamlit (*Operações → Deploy & Scripts*), os playbooks Ansible fazem isso automaticamente: copiam os arquivos, instalam as dependências e configuram os ambientes virtuais em todos os nós.

**2. Execução** — Ao clicar em "Rodar run.sh", o `run.sh` executa as seguintes etapas em sequência:

1. Para processos remanescentes de execuções anteriores e limpa os logs antigos
2. Sobe o servidor Flower via Ansible (`playbooks/deploy/start_server.yaml`)
3. Inicia o `tcpdump` para captura do tráfego de rede dos clientes
4. Dispara os clientes em todos os dispositivos via Ansible (`playbooks/deploy/start_clients.yaml`)
5. Aguarda o fim do servidor e dos clientes
6. Para o `tcpdump` e copia os logs de volta ao servidor (`playbooks/after_run/copy_to_server.yaml`)

**3. Resultados** — Com o experimento concluído, os logs ficam disponíveis para download pela aba de logs da GUI, com ou sem o `.pcap` de rede.

---

## 📊 Monitoramento de Hardware

Durante o experimento, cada dispositivo coleta métricas de hardware em paralelo com o treinamento. O `run_client_with_monitoring.py` inicia o script de monitoramento adequado para cada arquitetura (`monitor_pi.sh` nos Raspberry Pis via `vcgencmd`, `monitor_jetson.sh` nos Jetsons via `tegrastats`) em um grupo de processos separado, de forma que o encerramento do cliente garante o encerramento do monitor.

Os dados ficam organizados por dispositivo em:

```
app/logs/
├── client-<IP>/
│   ├── train.csv             # rodada, cid, acurácia e loss do treino
│   ├── evaluate.csv          # rodada, cid, acurácia e loss da avaliação
│   └── metrics/              # CPU, memória e temperatura (1 amostra/segundo)
├── client-<jetson-hostname>/
│   └── ...
└── pcaps/
    └── HH:MM:DD-MM-YYYY.pcap
```

---

## ⚙️ Configuração do Ambiente

### Pré-requisitos

- Python 3.11+
- Ansible 2.15+
- `uv` (gerenciador de ambientes Python nos dispositivos)
- Dispositivos acessíveis via SSH na rede configurada

### Inventário

O arquivo `ansible/inventory` **não é versionado** (contém IPs e credenciais da sua rede). Use o template incluído:

```bash
cp ansible/inventory.example ansible/inventory
# edite ansible/inventory com seus IPs e usuários
```

As senhas são armazenadas criptografadas via Ansible Vault em `ansible/group_vars/all/vault.yml`. Crie o arquivo de senha local:

```bash
echo "sua-senha-do-vault" > ~/.ansible_vault_pass
chmod 600 ~/.ansible_vault_pass
```

### GUI Streamlit

```bash
# No servidor central
cd HIAAC-FL-Testbed/
source .venv/bin/activate
streamlit run streamlit_app.py
```

---

## 📂 Estrutura do Repositório

```
HIAAC-FL-Testbed/
├── ansible/
│   ├── inventory.example            # template de inventário (copie e edite)
│   ├── group_vars/                  # variáveis por grupo (credenciais via vault)
│   └── playbooks/
│       ├── deploy/                  # start_server.yaml, start_clients.yaml
│       ├── setup/                   # copy_files, create_env, install_uv
│       ├── after_run/               # copy_to_server.yaml
│       └── stop/                    # stop_flower_clients.yaml
├── demo/                            # ← exemplo mínimo Docker (sem hardware)
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── server.py
│   ├── client.py
│   └── README.md
├── monitoring_scripts/
│   ├── monitor_pi.sh                # coleta métricas nos Raspberry Pis
│   ├── monitor_jetson.sh            # coleta métricas nos Jetsons (tegrastats)
│   └── run_client_with_monitoring.py
├── MODELOS_exemplos/
│   └── Modelos/                     # light, medium e heavy (zip + código fonte)
├── Arquivos_extra/
│   ├── Assets/                      # diagrama da arquitetura
│   └── *.png                        # screenshots da GUI
├── streamlit_app.py                 # interface gráfica principal
├── run.sh                           # script de execução do experimento
└── Guia_de_uso.md                   # guia rápido com screenshots
```
