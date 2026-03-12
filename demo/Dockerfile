FROM python:3.11-slim

WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código do demo
COPY server.py client.py ./

# Porta padrão do Flower
EXPOSE 8080

# Ponto de entrada parametrizável: SERVER_ROLE=server ou client
ENV SERVER_HOST=server \
    CLIENT_ID=0       \
    NUM_CLIENTS=2

CMD ["sh", "-c", \
     "if [ \"$SERVER_ROLE\" = 'server' ]; then python server.py; else python client.py; fi"]
