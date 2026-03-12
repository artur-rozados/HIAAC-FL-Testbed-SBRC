import os
os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
import tensorflow as tf
import flwr as fl
import numpy as np
from pathlib import Path

from flwr_datasets import FederatedDataset
from flwr_datasets.partitioner import IidPartitioner, DirichletPartitioner
from flwr_datasets.visualization import plot_label_distributions, plot_comparison_label_distribution
from model import create_model

# Diretório de cache para datasets
CACHE_DIR = Path.home() / ".cache" / "flwr_datasets"

class Cliente(fl.client.NumPyClient):
    def __init__(self, cid, niid, num_clients, dirichlet_alpha):
         self.cid             = int(cid)
         self.niid            = niid
         self.num_clients     = num_clients
         self.dirichlet_alpha = dirichlet_alpha

         self.x_train, self.y_train, self.x_test, self.y_test = self.load_data()
         self.model = create_model(input_shape=(28, 28, 1))
        #  self.model                                           = create_cifar10_cnn(self.x_train.shape)

    def get_parameters(self, config):
      return self.model.get_weights()

    def load_data(self):
        print(f"Loading data for client {self.cid}")
        
        # Cria diretório de cache se não existir
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Verifica se o dataset já está em cache
        cache_exists = (CACHE_DIR / "mnist").exists()
        if cache_exists:
            print(f"✓ Dataset MNIST encontrado em cache: {CACHE_DIR}")
        else:
            print(f"Baixando dataset MNIST para cache: {CACHE_DIR}")
        
        if self.niid:
            partitioner_train = DirichletPartitioner(num_partitions=self.num_clients, partition_by="label",
                                    alpha=self.dirichlet_alpha, min_partition_size=0,
                                    self_balancing=False)
            partitioner_test = DirichletPartitioner(num_partitions=self.num_clients, partition_by="label",
                                    alpha=self.dirichlet_alpha, min_partition_size=0,
                                    self_balancing=False)
        else:
            partitioner_train = IidPartitioner(num_partitions=self.num_clients)
            partitioner_test  = IidPartitioner(num_partitions=self.num_clients)

        # Load partitions
        fds = FederatedDataset(dataset='mnist', partitioners={"train": partitioner_train}, cache_dir=str(CACHE_DIR))
        train = fds.load_partition(self.cid)

        fds_eval = FederatedDataset(dataset='mnist', partitioners={"test": partitioner_test}, cache_dir=str(CACHE_DIR))
        test = fds_eval.load_partition(self.cid)

        x_train = np.stack(train['image']).astype("float32") / 255.0
        # Adicione esta linha:
        x_train = x_train.reshape(-1, 28, 28, 1)
        y_train = np.array(train['label'])
        
        x_test = np.stack(test['image']).astype("float32") / 255.0
        # Adicione esta linha:
        x_test = x_test.reshape(-1, 28, 28, 1)
        y_test = np.array(test['label'])

        return x_train, y_train, x_test, y_test

    def fit(self, parameters, config):
      print("Start Fit")
      self.model.set_weights(parameters)

      history = self.model.fit(self.x_train, self.y_train, epochs=1, batch_size=32)
      acc     = np.mean(history.history['accuracy'])
      loss    = np.mean(history.history['loss'])

      trained_parameters = self.model.get_weights()

      fit_msg = {
          'cid'     : self.cid,
          'accuracy': acc,
          'loss'    : loss,
      }

      self.log_client('./logs/train.csv', config['server_round'], acc, loss)
      return trained_parameters, len(self.x_train), fit_msg

    def evaluate(self, parameters, config):
      print("start evaluation")
      self.model.set_weights(parameters)
      loss, acc = self.model.evaluate(self.x_test, self.y_test, batch_size=32)
      eval_msg = {
          'cid'     : self.cid,
          'accuracy': acc,
          'loss'    : loss
      }
      self.log_client('./logs/evaluate.csv', config['server_round'], acc, loss)
      return loss, len(self.x_test), eval_msg

    def log_client(self, file_name, server_round, acc, loss):
        folder_path = os.path.dirname(file_name)
        
        if folder_path and not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)

        if server_round == 1 and os.path.isfile(file_name):
            os.remove(file_name)

        # Salva os dados
        with open(file_name, 'a') as file:
            file.write(f'{server_round}, {self.cid}, {acc}, {loss}\n')

print(f"Start client")

MAX_MESSAGE_LENGTH = 1024**3

fl.client.start_client(
    server_address=f'10.10.30.123:8080',
#    server_address=f'0.0.0.0:8080',
    client=Cliente(1, False, 14, 0.1).to_client(),
    grpc_max_message_length=MAX_MESSAGE_LENGTH,
)

# "-p asldk -g 0914"
