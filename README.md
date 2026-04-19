# FL-H.IAAC

**FL-H.IAAC** é um testbed para experimentos de Aprendizagem Federada (FL) em hardware heterogêneo real, com orquestração via Ansible, interface Streamlit para operação e monitoramento contínuo de métricas de hardware e logs de execução.

Este artefato acompanha o artigo submetido ao SBRC e tem como objetivo permitir a execução e avaliação de experimentos federados em um ambiente de laboratório com dispositivos reais, mantendo um fluxo reproduzível de deploy, execução, coleta e análise de resultados.

<p align="center">
  <img src="https://img.shields.io/badge/Ansible-EE0000?logo=ansible&logoColor=white" alt="Ansible">
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Raspberry%20Pi-A22846?logo=raspberrypi&logoColor=white" alt="Raspberry Pi">
  <img src="https://img.shields.io/badge/NVIDIA%20Jetson-76B900?logo=nvidia&logoColor=white" alt="NVIDIA Jetson">
  <img src="https://img.shields.io/badge/Telemetria-tcpdump-red" alt="Telemetria">
</p>

# Estrutura do readme.md

Este README está organizado nas seguintes partes:

1. Título e objetivo do artefato.
2. Selos solicitados para avaliação.
3. Informações básicas do ambiente e da arquitetura.
4. Dependências e requisitos externos.
5. Preocupações com segurança e restrições de acesso.
6. Instalação completa em ambiente limpo.
7. Teste mínimo para validação rápida.
8. Passo a passo dos experimentos e reivindicações.
9. Licença.

Estrutura principal do repositório:

```
HIAAC-FL-Testbed-SBRC/
├── ansible/
│   ├── build.yaml
│   ├── inventory
│   ├── inventory.example            # template de inventário
│   ├── orquestrador.yaml
│   ├── group_vars/                  # variáveis por grupo (credenciais via vault)
│   └── playbooks/
│       ├── after_run/               # copy_to_server.yaml
│       ├── deploy/                  # start_server.yaml, start_clients.yaml
│       ├── Flower/
│       ├── pi_jetsons/
│       ├── router/
│       ├── setup/                   # bootstrap, copy_files, create_env
│       ├── Templates/
│       ├── stop/                    # stop_flower_clients.yaml
│       ├── testes/
│       └── utils/
├── monitoring_scripts/
│   ├── monitor_pi.sh                # coleta métricas nos Raspberry Pis
│   ├── monitor_jetson.sh            # coleta métricas nos Jetsons (tegrastats)
│   └── run_client_with_monitoring.py
├── MODELOS_exemplos/
│   └── Modelos/                     # light, medium e heavy (zip + código fonte)
├── files_to_copy/                   # arquivos do modelo enviados aos dispositivos
│   └── logs/
├── streamlit_app.py                 # interface gráfica principal
├── requirements.txt                 # dependências da interface
├── run.sh                           # script de execução do experimento
├── force_stop.sh                    # para todos os processos imediatamente
└── LICENSE
```

# Selos Considerados

Os selos considerados para avaliação deste artefato são:

- **Artefatos Disponíveis (SeloD)**
- **Artefatos Funcionais (SeloF)**
- **Artefatos Sustentáveis (SeloS)**
- **Experimentos Reprodutíveis (SeloR)**

# Informações básicas

## Arquitetura do ambiente

O testbed é composto por três tipos de nós em rede isolada:

| Nó | Quantidade | Papel |
|----|--------|-------|
| **Servidor central** | 1 | Hospeda a GUI Streamlit, roda o servidor Flower e agrega logs |
| **Raspberry Pi** | Variável | Clientes FL com treinamento local no dispositivo |
| **NVIDIA Jetson** | Variável | Clientes FL com treinamento local no dispositivo |

> **O servidor precisa ter o IP fixo `10.10.30.123`**, pois os clientes usam esse endereço para se conectar ao servidor Flower (porta 8080).

A comunicação entre servidor e clientes durante o treinamento usa o framework [Flower (flwr)](https://flower.ai/) v1.9.0 na porta 8080, com estratégia FedAvg.

Para usar o testbed com sua própria infraestrutura, copie `ansible/inventory.example` para `ansible/inventory` e edite com seus IPs e credenciais.

## Fluxo geral de operação

A execução é feita pela interface Streamlit, que centraliza o ciclo de vida completo de um experimento — do upload do modelo até o download dos resultados.

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

**1. Upload do modelo** — Na aba *Arquivos*, faça upload de um `.zip` com o código do modelo. O Streamlit extrai os arquivos em `~/HIAAC-FL-Testbed-SBRC/files_to_copy/`, que é o diretório fonte para o deploy.

**2. Deploy** — Na aba *Operações*, clique em "Executar ansible-playbook". Este botão executa `ansible/build.yaml`, que:
- Copia os arquivos de `files_to_copy/` para `~/app/` em todos os dispositivos e no servidor local
- Cria o venv `~/app/.venv` em cada dispositivo usando `uv` e instala o `requirements.txt`

> O `~/app/` nos dispositivos e no servidor é um diretório **fora do repositório**, gerenciado pelos playbooks.

**3. Execução** — Clique em "Rodar run.sh". O script executa em sequência:

1. Para processos remanescentes de execuções anteriores
2. Limpa os logs antigos (no servidor e em todos os dispositivos)
3. Sobe o servidor Flower localmente via Ansible
4. Inicia o `tcpdump` filtrando a porta 8080 (tráfego gRPC do Flower)
5. Dispara os clientes em todos os dispositivos via Ansible
6. Monitora até o servidor encerrar (após todos os rounds)
7. Para o `tcpdump` e faz rsync dos logs de todos os dispositivos para `~/app/logs/`

**4. Resultados** — Na aba *Logs*, baixe os CSVs de métricas ou o pacote completo com o `.pcap`. Na aba *Gráficos*, visualize accuracy, loss e métricas de hardware interativamente.

## Monitoramento de hardware

Durante o experimento, cada dispositivo coleta métricas de hardware em paralelo com o treinamento. O `run_client_with_monitoring.py` inicia o script de monitoramento adequado para cada arquitetura (`monitor_pi.sh` nos Raspberry Pis via `vcgencmd`, `monitor_jetson.sh` nos Jetsons via `tegrastats`) em um grupo de processos separado, de forma que o encerramento do cliente garante o encerramento do monitor.

Os dados ficam organizados por dispositivo em:

```
app/logs/
├── client-<IP>/
│   ├── train.csv             # rodada, cid, acurácia e loss do treino
│   ├── evaluate.csv          # rodada, cid, acurácia e loss da avaliação
│   ├── hardware_metrics.csv  # métricas de hardware coletadas no cliente
│   └── tegrastats_raw.log    # disponível nos clientes Jetson
├── client-<jetson-hostname>/
│   └── ...
└── pcaps/
    └── HH:MM:DD-MM-YYYY.pcap
```

# Dependências

## Dependências da interface (servidor local)

- Python 3.11+
- streamlit
- pandas
- plotly

Arquivo de referência: `requirements.txt`.

## Dependências do modelo/execução federada (clientes e servidor FL)

- flwr==1.9.0
- flwr[simulation]
- tensorflow
- flwr_datasets

Arquivo de referência: `files_to_copy/requirements.txt`.

## Dependências de infraestrutura

- Ansible 2.15+
- uv
- tcpdump
- SSH funcional entre servidor e dispositivos

## Recursos de terceiros

- Flower: comunicação e estratégia federada.
- flwr_datasets: carga de datasets (pode exigir acesso à internet no primeiro download, dependendo do dataset usado).
- Ansible: execução em nós remotos em escala.

# Preocupações com segurança

1. O `run.sh` usa `sudo tcpdump` e `sudo pkill`; configure sudo sem senha apenas para esses binários e somente na máquina de orquestração.
2. O inventário e o vault contêm dados sensíveis (IPs, usuários e senhas). Não publique `ansible/inventory` nem `ansible/group_vars/all/vault.yml` sem anonimização.
3. Em ambiente público, use rede isolada para os dispositivos e restrinja acesso SSH por firewall/lista de IPs.
4. A demonstração remota via proxy (`http://143.106.73.34/`) exige credenciais privadas, que estão no apêndice submetido.
5. Recursos específicos/restritos (credenciais da proxy, detalhes de acesso remoto e qualquer material sensível) estão descritos no apêndice da submissão, conforme instruções.

# Instalação

### Pré-requisitos (na máquina / computador / servidor)

- Python 3.11+
- Ansible 2.15+
- `uv` instalado localmente
- `sudo` sem senha para `tcpdump` (usado pelo `run.sh` para captura de rede)
- Acesso SSH aos dispositivos do cluster

### 1. Instalar dependências

Instale **Python 3.11+**, **Ansible 2.15+** e **uv** usando o gerenciador de pacotes da sua distro/sistema. Exemplo no Ubuntu/Debian:

```bash
# Python 3.11 + venv (no Debian/Ubuntu vêm em pacotes separados; no Arch/macOS, venv já vem junto com o Python)
sudo apt install python3.11 python3.11-venv

# Ansible (exemplo: apt)
sudo apt install ansible

# tcpdump — necessário para captura de tráfego de rede durante os experimentos
sudo apt install tcpdump

# uv — instalador oficial, funciona em qualquer sistema
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clonar o repositório

> **Atenção:** Clone diretamente em `~` (home), não em subpastas como `~/Desktop`. Os playbooks Ansible constroem todos os caminhos a partir de `~/HIAAC-FL-Testbed-SBRC` — qualquer outro local vai quebrar o deploy.

```bash
cd ~
git clone https://github.com/artur-rozados/HIAAC-FL-Testbed-SBRC.git
cd ~/HIAAC-FL-Testbed-SBRC
```

Crie o venv e instale as dependências da GUI Streamlit:

```bash
# Usando uv (recomendado — já instalado no passo anterior)
uv venv .venv --python python3.11
uv pip install -r requirements.txt
```

> **Nota:** Este `.venv` é exclusivo da GUI Streamlit. Os dispositivos remotos e o servidor FL usam um venv separado, criado automaticamente pelo botão de deploy.

### 3. Configurar o inventário Ansible

O arquivo `ansible/inventory` não é versionado. Use o template incluso:

```bash
cp ansible/inventory.example ansible/inventory
# Edite com seus IPs e usuários
```

### 4. Configurar as credenciais (Ansible Vault)

As senhas dos dispositivos são armazenadas criptografadas em `ansible/group_vars/all/vault.yml` (não versionado). Use o template incluso:

```bash
cp ansible/group_vars/all/vault.yml.example ansible/group_vars/all/vault.yml
# Edite vault.yml com as senhas reais dos seus dispositivos
```

Depois criptografe e salve a senha de descriptografia:

```bash
ansible-vault encrypt ansible/group_vars/all/vault.yml
# Digite e confirme uma senha — esta é a senha do vault

echo "sua-senha-do-vault" > ~/.ansible_vault_pass
chmod 600 ~/.ansible_vault_pass
```

### 5. Configurar acesso SSH

O `ansible.cfg` usa autenticação por chave (`~/.ssh/id_ed25519`). Distribua a chave para todos os dispositivos:

```bash
# Gerar a chave (se ainda não tiver)
ssh-keygen -t ed25519

# Copiar para cada dispositivo
ssh-copy-id pi@<ip-do-raspberry>
ssh-copy-id jetson@<ip-do-jetson>
```

> **Jetsons com senha no inventário:** Se preferir autenticação por senha nos Jetsons (via `ansible_ssh_pass` no inventário), remova ou comente a linha `private_key_file` no `ansible.cfg`.

### 6. Bootstrap automático no deploy

O `ansible/build.yaml` executa um bootstrap idempotente antes do copy/venv. Em Pis/Jetsons recém-instaladas ele:

- instala apenas o que estiver faltando (`curl`, `python3`, `python3-venv`, `python3-pip`, `uv`)
- avisa (sem travar treino) se faltar `vcgencmd` em Raspberry Pi ou `tegrastats` em Jetson
- na etapa de criação de venv, usa `PYTHON_VERSION` (padrão `python3.11`); quando essa versão não estiver no sistema, o `uv` usa runtime gerenciado

> Se você aumentar o número de clientes, aumente também o `forks` no `ansible.cfg` para manter o deploy paralelo proporcional.

### 7. Autorizar `tcpdump` sem senha de sudo

Execute isto na sua máquina (o servidor que vai orquestrar os experimentos). O `run.sh` chama `sudo tcpdump` e `sudo pkill` para capturar e encerrar a captura de rede — sem essa configuração, o script pode travar esperando senha:

```bash
# Remove qualquer regra anterior (evita erro se houver arquivo inválido de tentativa anterior)
sudo rm -f /etc/sudoers.d/testbed-tcpdump

# Confirme os paths no seu sistema
which tcpdump   # normalmente /usr/bin/tcpdump
which pkill     # normalmente /usr/bin/pkill

# Aplique a regra (ajuste os paths acima se forem diferentes)
echo "$(whoami) ALL=(ALL) NOPASSWD: /usr/bin/tcpdump, /usr/bin/pkill" \
  | sudo tee /etc/sudoers.d/testbed-tcpdump
sudo chmod 440 /etc/sudoers.d/testbed-tcpdump

# Verifique que a sintaxe está correta
sudo visudo -c -f /etc/sudoers.d/testbed-tcpdump
```

> `tcpdump` e `pkill` ficam em `/usr/bin/` na grande maioria das distros Linux. Se `which` retornar outro path, substitua na linha do `echo` antes de aplicar.

### 8. Subir a GUI Streamlit

```bash
cd ~/HIAAC-FL-Testbed-SBRC
uv run streamlit run streamlit_app.py
# Acesse: http://localhost:8501 (ou outro IP que seja gerado)
```

### 9. Ajustar dispositivos monitorados na GUI

O painel de monitoramento em tempo real usa uma lista estática no arquivo `streamlit_app.py`:

- `DEVICE_IPS`: IPs que serão pingados
- `DEVICE_NAMES`: rótulos exibidos nos cards

Para adaptar ao seu laboratório, edite esses dois blocos no início do arquivo.
Boas práticas:

- mantenha os mesmos IPs em `DEVICE_IPS` e em `DEVICE_NAMES`
- use nomes curtos e estáveis (ex.: `Raspberry Pi A`, `Jetson A`)
- em repositório público, evite subir IPs reais da sua rede privada

# Teste mínimo

Esta seção valida se o artefato está funcional com o menor esforço possível para o revisor.

## Caminho A: validação local

1. Conclua a seção de instalação.
2. Suba a GUI:

```bash
cd ~/HIAAC-FL-Testbed-SBRC
uv run streamlit run streamlit_app.py
```

3. Verifique se as abas principais aparecem: Arquivos, Operações, Logs e Gráficos.
4. Faça upload de um modelo de exemplo (`MODELOS_exemplos/Modelos/*.zip`).
5. Execute o deploy na aba Operações.
6. Execute o `run.sh` e aguarde o término.
7. Valide na aba Logs se os pacotes são gerados e na aba Gráficos se há dados carregados.

## Caminho B: validação via proxy do laboratório

A proxy aponta para a GUI deste mesmo servidor de testbed, com os dispositivos do laboratório disponíveis para uso (incluindo Raspberry Pis e Jetsons ativos no ambiente de avaliação).

- URL: `http://143.106.73.34/`
- Credenciais: fornecidas sob solicitação aos autores

Caso o avaliador não possua credenciais, deve entrar em contato com os autores para liberação de acesso durante o período de avaliação.

# Experimentos

Esta seção descreve como executar os experimentos para alcançar as principais reivindicações do artigo.

## Reivindicações #1

**Reivindicação:** execução fim a fim de FL com coleta de logs de treino, avaliação, hardware e tráfego de rede.

### Arquivos de configuração relevantes

- `ansible/inventory`
- `ansible/group_vars/all/vault.yml`
- `files_to_copy/client.py`
- `files_to_copy/server.py`
- `run.sh`

### Passo a passo

1. Concluir instalação e configuração (inventário, vault e SSH).
2. Subir a GUI.
3. Fazer upload do modelo.
4. Executar deploy na aba Operações.
5. Executar `run.sh`.
6. Aguardar finalização do servidor Flower.
7. Confirmar logs em `~/app/logs/`.

### Tempo esperado

- Tipicamente entre 10 e 30 minutos, dependendo do número de dispositivos e da estabilidade da rede.

### Recursos esperados

- Servidor de orquestração com acesso SSH a todos os nós.
- Espaço em disco para logs e pcaps (recomendado > 2 GB por execução completa).

### Resultado esperado

- Presença de `train.csv`, `evaluate.csv`, `hardware_metrics.csv` por cliente.
- Presença de pcap em `~/app/logs/pcaps/`.
- Consolidação dos logs no servidor ao fim da execução.

## Reivindicações #2

**Reivindicação:** visualização e análise dos resultados no painel (métricas de FL e hardware por cliente).

### Arquivos de configuração relevantes

- `streamlit_app.py`
- `~/app/logs/` (gerado pela execução)

### Passo a passo

1. Garantir que a Reivindicação #1 foi concluída e os logs foram coletados.
2. Abrir a aba Gráficos na GUI.
3. Validar curvas de treino e avaliação por round.
4. Validar gráficos de hardware por cliente (memória, temperatura, tensão e métricas disponíveis).
5. Exportar logs pela aba Logs para análise externa, se necessário.

### Tempo esperado

- Carregamento dos gráficos em segundos a poucos minutos, dependendo do volume de logs.

### Recursos esperados

- Ambiente Python da GUI com `streamlit`, `pandas` e `plotly` instalados.

### Resultado esperado

- Gráficos renderizados sem erro para os logs disponíveis.
- Download dos artefatos de logs funcionando.


# LICENSE

Este projeto é distribuído sob a licença MIT, cujo texto completo segue abaixo:

MIT License

Copyright (c) 2026 H.IAAC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
