# backend/Dockerfile

# Usar uma imagem base oficial do Python para um ambiente leve e otimizado
FROM python:3.9-slim-buster

# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo de requisitos para o diretório de trabalho
COPY requirements.txt .

# Instalar as dependências Python
# O --no-cache-dir é para evitar o cache de pacotes, reduzindo o tamanho da imagem final
# O -r requirements.txt instala as dependências listadas
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da sua aplicação para o diretório de trabalho
# Copie o diretório 'src' e o 'main.py'
COPY . .

# Definir a porta que o container irá expor
# Esta porta deve corresponder à porta que o Flask/Gunicorn escutará (padrão 5000)
EXPOSE 5000

# Comando para rodar a aplicação usando Gunicorn
# Gunicorn é um servidor WSGI recomendado para produção Flask
# -w N: Número de workers (geralmente 2 * N_CORES + 1, ou um valor fixo como 4)
# --threads N: Número de threads por worker
# -b 0.0.0.0:PORTA: Vincula o servidor a todas as interfaces na porta definida
# main:app: Onde 'main' é o nome do seu arquivo Python (main.py) e 'app' é a instância do Flask (app = Flask(__name__))
CMD ["gunicorn", "-w", "4", "--threads", "2", "-b", "0.0.0.0:5000", "main:app"]

