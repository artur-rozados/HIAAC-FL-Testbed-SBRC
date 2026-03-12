# Guia de Uso — HIAAC-FL Testbed

Este guia cobre tudo o que um novo programador precisa saber para usar o testbed e adaptar seu próprio modelo de aprendizado federado para rodar aqui.

---

## O que é este testbed?

É uma infraestrutura de **Federated Learning (FL)** usando o framework [Flower (flwr)](https://flower.ai/). O testbed coordena um servidor central e vários dispositivos clientes físicos (Raspberry Pis e NVIDIA Jetsons) que treinam um modelo de forma distribuída, sem compartilhar dados brutos.

### Infraestrutura

| Componente | Quantidade | IPs | Hardware |
|---|---|---|---|
| Servidor (coordenador) | 1 | `10.10.30.123` | PC Linux |
| Raspberry Pi | 9 | `10.10.20.201` – `10.10.20.209` | RPi (ARM) |
| NVIDIA Jetson | 6 | `10.10.20.231` – `10.10.20.236` | Jetson (ARM + GPU) |

O servidor roda o `server.py`, que coordena as rodadas. Cada dispositivo roda o `client.py`, que treina localmente e envia pesos para o servidor.

---

## Pré-requisitos (apenas na primeira vez)

1. Estar conectado à rede do testbed (ex: via VPN ou na sala física)
2. Ter o arquivo `.ansible_vault_pass` em `~/.ansible_vault_pass` (contém a senha do Vault com credenciais dos dispositivos)
3. Ter o venv local criado (pasta `.venv/` na raiz do repositório):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Os dispositivos já precisam ter sido provisionados via `setup/` (instalação de Python, venv, dependências). Se ainda não foram, consulte os playbooks em `ansible/playbooks/setup/`.

---

## Como usar (fluxo normal de experimento)

### Passo 1 — Preparar o modelo

Crie ou edite os quatro arquivos do seu modelo (veja a seção [Adaptando seu modelo](#adaptando-seu-modelo)):
- `client.py`
- `model.py`
- `server.py`
- `requirements.txt`

Coloque-os na pasta `files_to_copy/`. Esses são os arquivos que serão enviados para os dispositivos.

### Passo 2 — Iniciar a GUI (opcional, mas recomendado)

```bash
cd ~/HIAAC-FL-Testbed
source .venv/bin/activate
streamlit run streamlit_app.py
```

Acesse pelo navegador: `http://10.10.30.123:8501`

### Passo 3 — Deploy (enviar arquivos para os dispositivos)

Via GUI: **Operações → Deploy & Scripts → "Executar ansible-playbook"**

Ou via terminal:
```bash
ansible-playbook -i ansible/inventory ansible/playbooks/setup/copy_files_to_devices.yaml \
  --vault-password-file ~/.ansible_vault_pass
```

Isso copia os arquivos de `files_to_copy/` para todos os Pis e Jetsons, e também copia os scripts de monitoramento.

### Passo 4 — Rodar o experimento

Via GUI: **"Rodar run.sh"**

Ou via terminal:
```bash
./run.sh
```

O `run.sh` faz automaticamente, em ordem:
1. Para processos de experimentos anteriores (`force_stop.sh`)
2. Limpa logs antigos do servidor (`app/logs/client-*`)
3. Limpa pcaps antigos (mantém os 3 mais recentes)
4. Limpa logs nos dispositivos remotos (playbook `clean_all_logs.yaml`)
5. Inicia o servidor em background (`start_server.yaml`)
6. Aguarda 20s para o servidor subir
7. Inicia captura de rede com `tcpdump` na porta 8080 (tráfego Flower/gRPC)
8. Inicia os clientes em todos os dispositivos em background (`start_clients.yaml`)
9. Aguarda o servidor terminar (monitora o processo `server.py`)
10. Para o `tcpdump` e salva o `.pcap` em `pcaps/`
11. Copia os logs de todos os dispositivos para `app/logs/` (`copy_to_server.yaml`)

### Passo 5 — Verificar os resultados

Os logs ficam em:
```
app/logs/
├── client-10.10.20.201/
│   ├── train.csv            # acurácia e loss por rodada (treino)
│   ├── evaluate.csv         # acurácia e loss por rodada (avaliação)
│   └── hardware_metrics.csv # CPU, memória, temperatura a cada segundo
├── client-jetson/
│   ├── train.csv
│   ├── evaluate.csv
│   └── hardware_metrics.csv
│   └── tegrastats_raw.log   # log bruto do tegrastats (apenas Jetsons)
├── ...
└── pcaps/
    └── HH:MM:DD-MM-YYYY.pcap  # captura de rede do experimento
```

Formato do `train.csv` e `evaluate.csv`:
```
rodada, cid, acurácia, loss
1, 3, 0.9123, 0.2451
2, 3, 0.9341, 0.1987
...
```

---

## Adaptando seu modelo

Esta é a parte mais importante. Para rodar seu próprio modelo, você precisa criar quatro arquivos.

### Estrutura obrigatória

```
files_to_copy/
├── client.py        ← lógica do cliente FL
├── model.py         ← definição da arquitetura
├── server.py        ← lógica do servidor FL
└── requirements.txt ← dependências Python
```

---

### `model.py` — Defina sua arquitetura

Este arquivo deve expor **uma função que cria e compila o modelo**. O nome da função pode ser qualquer coisa, mas ela deve receber o `input_shape` e retornar o modelo compilado.

```python
import tensorflow as tf

def create_model(input_shape=(28, 28, 1), num_classes=10):
    model = tf.keras.models.Sequential([
        tf.keras.layers.Input(shape=input_shape),
        # ... suas camadas aqui ...
        tf.keras.layers.Dense(num_classes, activation='softmax'),
    ])
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return model
```

> **Observação:** os dispositivos não têm GPU acessível via TensorFlow por padrão. Para desabilitar a GPU (necessário nas Pis, recomendado nas Jetsons para evitar conflitos):
> ```python
> import os
> os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
> ```

---

### `client.py` — Lógica do cliente Flower

O cliente deve herdar de `fl.client.NumPyClient` e implementar três métodos obrigatórios: `get_parameters`, `fit` e `evaluate`.

**Esqueleto mínimo:**

```python
import os
os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
import flwr as fl
import numpy as np
from model import create_model

class Cliente(fl.client.NumPyClient):
    def __init__(self, cid, ...):
        self.cid = int(cid)
        self.x_train, self.y_train, self.x_test, self.y_test = self.load_data()
        self.model = create_model(input_shape=...)

    def get_parameters(self, config):
        # Retorna os pesos atuais do modelo como lista de arrays numpy
        return self.model.get_weights()

    def fit(self, parameters, config):
        # Recebe pesos do servidor, treina localmente, devolve pesos atualizados
        self.model.set_weights(parameters)
        history = self.model.fit(self.x_train, self.y_train, epochs=1, batch_size=32)
        acc  = float(np.mean(history.history['accuracy']))
        loss = float(np.mean(history.history['loss']))

        # LOG OBRIGATÓRIO — o testbed coleta este arquivo
        self.log_client('./logs/train.csv', config['server_round'], acc, loss)

        return self.model.get_weights(), len(self.x_train), {'cid': self.cid, 'accuracy': acc}

    def evaluate(self, parameters, config):
        # Recebe pesos do servidor, avalia no conjunto de teste
        self.model.set_weights(parameters)
        loss, acc = self.model.evaluate(self.x_test, self.y_test, batch_size=32)

        # LOG OBRIGATÓRIO — o testbed coleta este arquivo
        self.log_client('./logs/evaluate.csv', config['server_round'], acc, loss)

        return loss, len(self.x_test), {'cid': self.cid, 'accuracy': acc}

    def log_client(self, file_name, server_round, acc, loss):
        # Cria a pasta se não existir
        folder_path = os.path.dirname(file_name)
        if folder_path and not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        # Apaga o arquivo na rodada 1 para não misturar experimentos
        if server_round == 1 and os.path.isfile(file_name):
            os.remove(file_name)
        with open(file_name, 'a') as f:
            f.write(f'{server_round}, {self.cid}, {acc}, {loss}\n')

    def load_data(self):
        # Carregue e retorne seus dados aqui
        # Deve retornar: x_train, y_train, x_test, y_test
        raise NotImplementedError

# Inicialização — ajuste os parâmetros conforme seu experimento
MAX_MESSAGE_LENGTH = 1024**3
fl.client.start_client(
    server_address='10.10.30.123:8080',
    client=Cliente(cid=1).to_client(),
    grpc_max_message_length=MAX_MESSAGE_LENGTH,
)
```

> **Importante:** o caminho `'./logs/train.csv'` é relativo. O Ansible inicia o cliente com `chdir` apontando para a pasta do app no dispositivo, então o caminho funciona corretamente. Não mude para caminhos absolutos sem necessidade.

---

### `server.py` — Lógica do servidor Flower

O servidor herda de `fl.server.strategy.FedAvg` e implementa as etapas de agregação. O mínimo necessário:

```python
import os
os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
import flwr as fl
from flwr.common import parameters_to_ndarrays, ndarrays_to_parameters, FitIns, EvaluateIns
from flwr.server.strategy.aggregate import aggregate

class Servidor(fl.server.strategy.FedAvg):
    def __init__(self, num_clients, fraction_fit=1.0):
        super().__init__(
            fraction_fit=fraction_fit,
            min_available_clients=4  # mínimo de clientes para a rodada começar
        )
        self.num_clients = num_clients

    def configure_fit(self, server_round, parameters, client_manager):
        config = {'server_round': server_round}
        fit_ins = FitIns(parameters, config)
        sample_size, min_num_clients = self.num_fit_clients(client_manager.num_available())
        clients = client_manager.sample(num_clients=sample_size, min_num_clients=min_num_clients)
        return [(client, fit_ins) for client in clients]

    def aggregate_fit(self, server_round, results, failures):
        parameters_list = [
            [parameters_to_ndarrays(fit_res.parameters), int(fit_res.num_examples)]
            for _, fit_res in results
        ]
        agg = ndarrays_to_parameters(aggregate(parameters_list))
        return agg, {}

    def configure_evaluate(self, server_round, parameters, client_manager):
        config = {'server_round': server_round}
        evaluate_ins = EvaluateIns(parameters, config)
        sample_size, min_num_clients = self.num_evaluation_clients(client_manager.num_available())
        clients = client_manager.sample(num_clients=sample_size, min_num_clients=min_num_clients)
        return [(client, evaluate_ins) for client in clients]

    def aggregate_evaluate(self, server_round, results, failures):
        if not results:
            return None, {}
        accuracies = [r.metrics['accuracy'] for _, r in results]
        avg_acc = sum(accuracies) / len(accuracies)
        print(f"Rodada {server_round} — acurácia média: {avg_acc:.4f}")
        return avg_acc, {}

MAX_MESSAGE_LENGTH = 1024**3
fl.server.start_server(
    server_address='0.0.0.0:8080',
    config=fl.server.ServerConfig(num_rounds=15),  # ajuste o número de rodadas
    strategy=Servidor(num_clients=15, fraction_fit=1.0),
    grpc_max_message_length=MAX_MESSAGE_LENGTH,
)
```

**Parâmetros importantes:**

| Parâmetro | O que faz |
|---|---|
| `num_rounds` | Número de rodadas de treinamento federado |
| `min_available_clients` | Mínimo de clientes conectados para iniciar uma rodada |
| `fraction_fit` | Fração de clientes disponíveis usados por rodada (1.0 = todos) |

---

### `requirements.txt` — Dependências

Liste as dependências Python do seu modelo. Exemplo mínimo:

```
flwr==1.9.0
tensorflow
flwr_datasets
```

> As dependências são instaladas no venv de cada dispositivo durante o setup (`create_env_on_devices.yaml`). Se adicionar novas dependências, rode o setup novamente antes do experimento.

---

## Monitoramento de hardware (automático)

O testbed coleta métricas de hardware automaticamente durante o treinamento — você não precisa fazer nada.

O script `run_client_with_monitoring.py` é executado em cada dispositivo como wrapper do `client.py`. Ele inicia o script de monitoramento (`monitor.sh`) em background e o encerra quando o cliente termina.

**Métricas coletadas nos Raspberry Pis** (`hardware_metrics.csv`):
```
timestamp, cpu_temp_C, core_voltage_V, cpu_load_1min, cpu_load_5min, cpu_load_15min,
mem_total_MB, mem_used_MB, mem_free_MB, mem_available_MB, mem_usage_percent
```

**Métricas coletadas nas Jetsons** (`hardware_metrics.csv`):
```
timestamp, cpu_usage_percent, mem_used_MB, mem_total_MB, mem_usage_percent,
gpu_usage_percent, temp_CPU_C, temp_GPU_C, temp_thermal_C, power_mW
```

As Jetsons também geram `tegrastats_raw.log` com a saída bruta do `tegrastats`.

---

## Captura de rede (pcap)

O `run.sh` captura automaticamente o tráfego gRPC (porta 8080) durante o experimento usando `tcpdump`. O arquivo é salvo em:

```
pcaps/HH:MM:DD-MM-YYYY.pcap
```

Apenas os **3 pcaps mais recentes** são mantidos (os mais antigos são deletados automaticamente no início de cada `run.sh`). O pcap do experimento mais recente também é copiado para `app/logs/pcaps/` junto com os logs dos clientes.

---

## Estrutura de pastas relevante

```
HIAAC-FL-Testbed/
├── run.sh                        # script principal — roda o experimento completo
├── force_stop.sh                 # para todos os processos de experimento
├── streamlit_app.py              # GUI web (Streamlit)
├── ansible.cfg                   # configuração do Ansible
├── ansible/
│   ├── inventory                 # lista de hosts (Pis, Jetsons) e credenciais
│   ├── group_vars/all.yml        # variáveis de caminho globais
│   └── playbooks/
│       ├── setup/                # provisionar dispositivos (instalar venv, deps)
│       ├── deploy/               # iniciar servidor e clientes
│       ├── after_run/            # copiar logs de volta para o servidor
│       └── utils/                # utilitários (limpar logs, obter caminhos)
├── files_to_copy/                # ← coloque seu modelo aqui para deploy
│   ├── client.py
│   ├── model.py
│   ├── server.py
│   └── requirements.txt
├── monitoring_scripts/           # scripts de monitoramento (copiados automaticamente)
│   ├── monitor_pi.sh
│   ├── monitor_jetson.sh
│   └── run_client_with_monitoring.py
├── app/                          # cópia local do que está rodando no servidor
│   └── logs/                     # logs copiados dos dispositivos após o experimento
├── pcaps/                        # capturas de rede
└── testes/                       # exemplos de modelos (light, medium, heavy training)
```

---

## Exemplos de modelos prontos

Em `testes/` há exemplos de modelos com diferentes cargas computacionais:

| Pasta | Modelo | Uso |
|---|---|---|
| `testes/light-training/` | Rede simples (poucos parâmetros) | Testes rápidos, dispositivos fracos |
| `testes/medium-training/` | CNN média (Conv2D + Dense) | Experimentos padrão |
| `testes/heavy-training/` | CNN profunda (muitas camadas Dense) | Carga alta, benchmark de hardware |

Copie os arquivos de qualquer um para `files_to_copy/` e rode o deploy para testar.

---

## Solução de problemas comuns

### Um dispositivo não conecta / não participa do treinamento

1. Verifique se o dispositivo está ligado e na rede: `ping 10.10.20.201`
2. Verifique o log do Ansible (`client.log` gerado pelo `run.sh`)
3. Se for uma Jetson com problema de `~/.ansible/tmp`, reinicie o dispositivo — o problema some. (O `ansible.cfg` já está configurado com `remote_tmp=/tmp/.ansible_tmp` para evitar isso.)

### O servidor não inicia

Verifique `app/server.log`. Causa comum: porta 8080 já em uso de experimento anterior. Rode `./force_stop.sh` e tente novamente.

### Cliente termina mas não treinou (acurácia não aparece nos logs)

Verifique `app/logs/client-IP/client.log`. Causa comum: erro de import no `client.py` ou `model.py`, ou dataset não conseguiu ser baixado.

### Dataset MNIST demora muito para baixar

O cliente cacheia o dataset em `~/.cache/flwr_datasets/mnist/` no dispositivo. Na primeira execução demora; nas seguintes é instantâneo.

### Adicionar um novo dispositivo ao testbed

1. Adicione o IP/hostname em `ansible/inventory` no grupo correto (`Raspberry_Pi` ou `Jetsons`)
2. Para Jetsons: adicione a senha no vault (`ansible-vault edit ansible/vault.yml`)
3. Rode o setup completo: `ansible-playbook -i ansible/inventory ansible/playbooks/setup/copy_files_to_devices.yaml --vault-password-file ~/.ansible_vault_pass`
4. Rode `create_env_on_devices.yaml` para instalar o venv e dependências
