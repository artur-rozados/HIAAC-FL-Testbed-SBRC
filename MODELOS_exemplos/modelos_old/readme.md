
Para rodar os experimentos federados, e você for alterar a quantidade de cliente que irão participar. Dessa forma, lembre-se de alterar o número de clientes no servidor.

# LEMBRESE SE SALVAR E CRIAR UMA BRANCH PARA OS TESTES


Alterar disso:
```python
strategy=Servidor(num_clients=5, dirichlet_alpha=0.1, fraction_fit=0.2)
```
para isso:
```python
strategy=Servidor(num_clients=NUMERO_DE_CLIENTES_DESEJADO, dirichlet_alpha=0.1, fraction_fit=0.2)
```

Lembre-se fraction_fit é uma porcentagem, o resultado deve ser >= 2.

## Metricas
tensão (cpu) | vcgencmd measure_volts core
Temperatura | vcgencmd measure_temp
Carga da CPU | uptime ou top
memória RAM
Outras métricas de sistema relevante

## Teste individual
-> Rodar 10 vezes cada para cada device
- light_training.py
- medium_training.py
- heavy_training.py

## Teste federado
-> Rodar 5 vezes cada em todos devices disponíveis
- light-training folder
- medium-training folder
- heavy-training folder


## Teste federado
-> Rodar 5 vezes cada
Nesse teste, você deve ir reduzindo a quantidade de dispositivos até que nenhum device se desligue durante o treinamento.
- light-training folder
- medium-training folder
- heavy-training folder
