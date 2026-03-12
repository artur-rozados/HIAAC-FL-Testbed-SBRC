# Scripts de Monitoramento

Essa pasta guarda os scripts que coletam dados de hardware (CPU, RAM, temp, etc) durante os testes.

Eles são copiados automaticamente para as Raspberry Pis e Jetsons pelo Ansible.

## O que tem aqui:

* `monitor_pi.sh`: Usa `vcgencmd` e comandos do sistema pra pegar dados da Pi.
* `monitor_jetson.sh`: Usa `tegrastats` pra pegar dados da Jetson.
* `run_client_with_monitoring.py`: Script "wrapper" que roda no lugar do `client.py` original. Ele cuida de iniciar a coleta de dados antes do treino e parar depois.

**Obs:** Não precisa alterar nada aqui manualmente. Se mexer no `client.py` na pasta `files_to_copy`, o sistema continua usando esses scripts aqui para monitoramento.

