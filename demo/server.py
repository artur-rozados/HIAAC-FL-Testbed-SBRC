"""
Servidor Flower simplificado para demo local/Docker.
FedAvg com 2 clientes, 3 rounds — executa em ~2 minutos.
"""
import flwr as fl
from flwr.server.strategy import FedAvg

MAX_MESSAGE_LENGTH = 512 * 1024 * 1024  # 512 MB

strategy = FedAvg(
    fraction_fit=1.0,
    fraction_evaluate=1.0,
    min_fit_clients=2,
    min_evaluate_clients=2,
    min_available_clients=2,
)

print("☁  Servidor Flower iniciando em 0.0.0.0:8080 …")
fl.server.start_server(
    server_address="0.0.0.0:8080",
    config=fl.server.ServerConfig(num_rounds=3),
    strategy=strategy,
    grpc_max_message_length=MAX_MESSAGE_LENGTH,
)
