import numpy as np
import time
from tensorflow.keras.datasets import mnist
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.utils import to_categorical

def create_light_model(input_shape=(28, 28, 1), num_classes=10):
    """Modelo Leve: CNN com uma camada convolucional e uma densa simples."""
    model = Sequential([
        Input(shape=input_shape),
        Conv2D(32, kernel_size=3, activation='relu', padding='same'),
        MaxPooling2D(pool_size=2),
        Conv2D(64, kernel_size=3, activation='relu', padding='same'),
        MaxPooling2D(pool_size=2),
        Conv2D(128, kernel_size=3, activation='relu', padding='same'),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax'),
    ])
    return model

def create_medium_model(input_shape=(28, 28, 1), num_classes=10):
    """Modelo Médio: CNN com duas camadas convolucionais e duas densas."""
    model = Sequential([
        Input(shape=input_shape),
        Conv2D(32, kernel_size=3, activation='relu', padding='same'),
        MaxPooling2D(pool_size=2),
        Conv2D(64, kernel_size=3, activation='relu', padding='same'),
        MaxPooling2D(pool_size=2),
        Conv2D(128, kernel_size=3, activation='relu', padding='same'),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(256, activation='relu'),
        Dropout(0.5),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax'),
    ])
    return model


def create_heavy_model(input_shape=(28, 28, 1), num_classes=10):
    """Modelo Pesado: CNN mais profunda e larga, com mais camadas convolucionais e densas."""
    model = Sequential([
        Input(shape=input_shape),
        Conv2D(32, kernel_size=3, activation='relu', padding='same'),
        MaxPooling2D(pool_size=2),
        Conv2D(64, kernel_size=3, activation='relu', padding='same'),
        MaxPooling2D(pool_size=2),
        Conv2D(128, kernel_size=3, activation='relu', padding='same'),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(256, activation='relu'),
        Dropout(0.5),
        Dense(512, activation='relu'),
        Dropout(0.5),
        Dense(256, activation='relu'),
        Dropout(0.5),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax'),
    ])

    return model

def train_and_evaluate(model_fn, model_name, x_train, y_train, x_test, y_test):
    print(f"\n--- Iniciando Treinamento: {model_name} ---")
    
    model = model_fn(input_shape=x_train.shape[1:])
    model.compile(optimizer='adam', 
                  loss='categorical_crossentropy', 
                  metrics=['accuracy'])
    
    start_time = time.time()
    
    history = model.fit(x_train, y_train, 
                        epochs=5,                 # Reduza as épocas para teste rápido
                        batch_size=32,            # Use um batch_size razoável
                        validation_data=(x_test, y_test),
                        verbose=1)
    
    end_time = time.time()
    
    # 3. Avaliação
    loss, acc = model.evaluate(x_test, y_test, verbose=0)
    
    # 4. Resultados
    training_time = end_time - start_time
    print(f"\nResultados {model_name}:")
    print(f"  Total de Parâmetros: {model.count_params()}")
    print(f"  Tempo de Treinamento: {training_time:.2f} segundos")
    print(f"  Acurácia de Teste: {acc*100:.2f}%")
    
    return model

# 1. Carregar dados
# Este passo baixa os dados se não estiverem em cache (necessita de internet na primeira execução)
(x_train, y_train), (x_test, y_test) = mnist.load_data()

# 2. Normalização: Converte para float32 e escala os valores de 0 a 1
x_train = x_train.astype('float32') / 255.0
x_test = x_test.astype('float32') / 255.0

# 3. Reformatar: Adicionar dimensão do canal (para CNNs)
# De (N, 28, 28) para (N, 28, 28, 1)
x_train = np.expand_dims(x_train, -1)
x_test = np.expand_dims(x_test, -1)

# 4. Codificação one-hot dos rótulos
y_train = to_categorical(y_train, num_classes=10)
y_test = to_categorical(y_test, num_classes=10)

input_shape = x_train.shape[1:]

model_light = train_and_evaluate(create_light_model, "Modelo Leve", x_train, y_train, x_test, y_test)
# model_medium = train_and_evaluate(create_medium_model, "Modelo Médio", x_train, y_train, x_test, y_test)
# # O modelo pesado pode ser muito lento; monitore o uso de CPU/Memória.
# model_heavy = train_and_evaluate(create_heavy_model, "Modelo Pesado", x_train, y_train, x_test, y_test)