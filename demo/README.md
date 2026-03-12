# Demo — Exemplo Mínimo de Execução (Docker)

Este diretório contém um exemplo mínimo e **independente de hardware** do HIAAC-FL-Testbed. Ele roda um experimento de Aprendizagem Federada com **1 servidor e 2 clientes** em containers locais, usando o dataset MNIST e uma CNN leve — sem necessidade de Raspberry Pis, Jetsons ou Ansible.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) ≥ 24.x
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.x
- ~2 GB de RAM livres

## Execução

```bash
# 1. Entre na pasta do demo
cd demo/

# 2. Suba os containers (build automático na primeira vez)
docker compose up --build

# 3. Aguarde — o experimento completa 3 rounds (~2 min, dependendo da máquina)
#    Você verá logs de cada round nos containers client0 e client1.
```

Para parar:

```bash
docker compose down
```

## O que acontece

| Serviço  | Papel                                                         |
|----------|---------------------------------------------------------------|
| `server` | Servidor Flower com estratégia FedAvg, 3 rounds, 2 clientes  |
| `client0`| Cliente 0 — treina na partição 0 do MNIST (IID)              |
| `client1`| Cliente 1 — treina na partição 1 do MNIST (IID)              |

A cada round, cada cliente:
1. Recebe os pesos globais do servidor
2. Treina localmente por 1 época no seu pedaço do MNIST
3. Envia os pesos atualizados de volta
4. O servidor agrega via FedAvg e reporta a acurácia média

## Saída esperada (exemplo)

```
server   | ☁  Servidor Flower iniciando em 0.0.0.0:8080 …
client0  | 🔗 Cliente 0 conectando a server:8080 …
client1  | 🔗 Cliente 1 conectando a server:8080 …
client0  | [Cliente 0] Treino  — round 1 | acc=0.8312 loss=0.5401
client1  | [Cliente 1] Treino  — round 1 | acc=0.8291 loss=0.5488
...
server   | FL finished in X.XXs
```

## Customização

| Variável de ambiente | Padrão | Descrição                    |
|----------------------|--------|-------------------------------|
| `NUM_CLIENTS`        | `2`    | Total de clientes no experimento |
| `CLIENT_ID`          | `0`    | ID do cliente (0 … N-1)      |
| `SERVER_HOST`        | `server`| Hostname/IP do servidor Flower|

Para alterar o número de rounds, edite a linha `num_rounds=3` em `server.py`.

## Diferenças em relação ao testbed real

No testbed físico, em vez de containers Docker:
- Os clientes são Raspberry Pis e NVIDIA Jetsons em rede isolada
- O Ansible faz o deploy automático do modelo e inicia os processos remotamente
- O monitoramento coleta CPU, memória e temperatura de cada dispositivo em tempo real
- Os resultados ficam disponíveis para download via interface Streamlit
