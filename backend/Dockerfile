# backend/Dockerfile

# --- Estágio 1: Builder ---
# Este estágio instala as dependências. O resultado será copiado para o estágio final,
# mas as ferramentas de build e o cache não, mantendo a imagem final enxuta.
FROM python:3.9.18-slim-buster AS builder

WORKDIR /app

# Instala ferramentas de build que podem ser necessárias para algumas bibliotecas Python.
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential

# Instala as dependências em um diretório de usuário, que é mais seguro
# e facilita a cópia para o próximo estágio.
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Estágio 2: Final ---
# Este é o estágio final, que cria a imagem de produção.
# Ele é baseado na mesma imagem leve, mas não contém as ferramentas de build.
FROM python:3.9.18-slim-buster

WORKDIR /app

# Cria um usuário não-root para executar a aplicação, o que é uma prática
# de segurança essencial para evitar que a aplicação tenha permissões elevadas.
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Copia apenas as dependências pré-instaladas do estágio 'builder'.
# Isso evita copiar o cache e as ferramentas de build, reduzindo o tamanho da imagem.
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Adiciona o diretório de pacotes do usuário ao PATH do sistema.
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Copia o código da aplicação para o diretório de trabalho.
# O .dockerignore garantirá que arquivos desnecessários não sejam copiados.
COPY --chown=appuser:appuser . .

# Expõe a porta que o Gunicorn irá usar.
EXPOSE 5000

# Comando final para iniciar a aplicação usando Gunicorn.
# O uso de 'exec' garante que o Gunicorn se torne o processo principal (PID 1),
# o que melhora o gerenciamento de sinais (como parar o container).
CMD ["gunicorn", "--workers", "4", "--threads", "2", "--bind", "0.0.0.0:5000", "main:app"]
