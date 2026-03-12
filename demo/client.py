"""
Cliente Flower simplificado para demo local/Docker.
Treina uma CNN leve no dataset MNIST (IID).
"""
import os
import numpy as np
import flwr as fl
import tensorflow as tf

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # força CPU

SERVER_HOST = os.environ.get("SERVER_HOST", "localhost")
CLIENT_ID   = int(os.environ.get("CLIENT_ID", "0"))
NUM_CLIENTS = int(os.environ.get("NUM_CLIENTS", "2"))
NUM_ROUNDS  = int(os.environ.get("NUM_ROUNDS", "3"))

MAX_MESSAGE_LENGTH = 512 * 1024 * 1024


def create_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(28, 28, 1)),
        tf.keras.layers.Conv2D(32, (3, 3), activation="relu"),
        tf.keras.layers.MaxPooling2D(),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def load_data(client_id: int, num_clients: int):
    """Carrega o MNIST e particiona IID entre os clientes."""
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    x_train = x_train.astype("float32") / 255.0
    x_test  = x_test.astype("float32")  / 255.0
    x_train = x_train[..., np.newaxis]
    x_test  = x_test[..., np.newaxis]

    # Partição IID simples por índice
    idx_train = np.arange(len(x_train))
    idx_test  = np.arange(len(x_test))
    train_part = np.array_split(idx_train, num_clients)[client_id]
    test_part  = np.array_split(idx_test,  num_clients)[client_id]

    return (x_train[train_part], y_train[train_part],
            x_test[test_part],  y_test[test_part])


class FlowerClient(fl.client.NumPyClient):
    def __init__(self, cid, num_clients):
        self.cid   = cid
        self.model = create_model()
        self.x_train, self.y_train, self.x_test, self.y_test = load_data(cid, num_clients)
        print(f"[Cliente {cid}] {len(self.x_train)} amostras de treino carregadas.")

    def get_parameters(self, config):
        return self.model.get_weights()

    def fit(self, parameters, config):
        self.model.set_weights(parameters)
        history = self.model.fit(
            self.x_train, self.y_train,
            epochs=1, batch_size=32, verbose=0,
        )
        acc  = float(history.history["accuracy"][-1])
        loss = float(history.history["loss"][-1])
        print(f"[Cliente {self.cid}] Treino  — round {config.get('server_round','?')} | acc={acc:.4f} loss={loss:.4f}")
        return self.model.get_weights(), len(self.x_train), {"accuracy": acc, "loss": loss}

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        loss, acc = self.model.evaluate(self.x_test, self.y_test, batch_size=32, verbose=0)
        print(f"[Cliente {self.cid}] Avaliação — round {config.get('server_round','?')} | acc={acc:.4f} loss={loss:.4f}")
        return loss, len(self.x_test), {"accuracy": acc}


print(f"🔗 Cliente {CLIENT_ID} conectando a {SERVER_HOST}:8080 …")
fl.client.start_client(
    server_address=f"{SERVER_HOST}:8080",
    client=FlowerClient(CLIENT_ID, NUM_CLIENTS).to_client(),
    grpc_max_message_length=MAX_MESSAGE_LENGTH,
)
