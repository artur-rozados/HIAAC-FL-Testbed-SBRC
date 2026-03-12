import os
os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
from flwr.common import parameters_to_ndarrays, ndarrays_to_parameters
from flwr.common import FitIns, EvaluateIns
from flwr.server.strategy.aggregate import aggregate
import random
import flwr as fl

class Servidor(fl.server.strategy.FedAvg):
    def __init__(self, num_clients, dirichlet_alpha, fraction_fit=0.2):
        self.num_clients     = num_clients
        self.dirichlet_alpha = dirichlet_alpha

        super().__init__(fraction_fit=fraction_fit, min_available_clients=num_clients)

    def configure_fit(self, server_round, parameters, client_manager):
        """Configure the next round of training."""
        print("start configure fit")
        config = {
            'server_round': server_round,
        }
        fit_ins = FitIns(parameters, config)


        sample_size, min_num_clients = self.num_fit_clients(
            client_manager.num_available()
        )
        clients = client_manager.sample(
            num_clients=sample_size, min_num_clients=min_num_clients
        )
        # print(clients)
        return [(client, fit_ins) for client in clients]

    def aggregate_fit(self, server_round, results, failures):
        print(f"start aggregate fit: Round {server_round}")
        parameters_list = []

        for _, fit_res in results:
            # print(f"Rodada {server_round} resultados de treinamento: {fit_res}")
            parameters = parameters_to_ndarrays(fit_res.parameters)
            exemplos   = int(fit_res.num_examples)

            parameters_list.append([parameters, exemplos])

        agg_parameters = aggregate(parameters_list)
        agg_parameters = ndarrays_to_parameters(agg_parameters)

        return agg_parameters, {}

    def configure_evaluate(self, server_round, parameters, client_manager):
        print(f"start configure evaluate: Round {server_round}")
        
        config = {
            'server_round': server_round,
        }

        evaluate_ins = EvaluateIns(parameters, config)


        sample_size, min_num_clients = self.num_evaluation_clients(
            client_manager.num_available()
        )

        clients = client_manager.sample(
            num_clients=sample_size, min_num_clients=min_num_clients
        )

        return [(client, evaluate_ins) for client in clients]

    def aggregate_evaluate(self, server_round, results, failures):
        print(f"start aggregate evaluate: Round {server_round}")
        
        accuracies = []

        for _, response in results:
            acc = response.metrics['accuracy']
            accuracies.append(acc)

        avg_acc = sum(accuracies)/len(accuracies)
        print(f"Rodada {server_round} acurácia agregada: {avg_acc}")

        return avg_acc, {}

print("Start server")
MAX_MESSAGE_LENGTH = 1024**3
fl.server.start_server(
    server_address=f'0.0.0.0:8080',
    config=fl.server.ServerConfig(num_rounds = 15),
    strategy=Servidor(num_clients=2, dirichlet_alpha=0.1, fraction_fit=1),
    grpc_max_message_length=MAX_MESSAGE_LENGTH,
)
