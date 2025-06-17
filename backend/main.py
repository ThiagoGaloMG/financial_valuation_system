# backend/main.py

import os
import sys
import logging
from flask import Flask
from flask_cors import CORS

# --- Configuração do Logging ---
# É a primeira coisa a ser feita para garantir que todos os logs,
# inclusive os de erro na inicialização, sejam devidamente capturados.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

# --- Configuração do Path da Aplicação ---
# Adiciona o diretório 'src' ao path do sistema. Isso permite que o Python
# encontre os módulos locais (como 'routes' e 'database_manager').
# Ex: from routes.financial import financial_bp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# --- Bloco de Importação Crítico ---
# A aplicação não pode funcionar se as rotas não forem carregadas.
# Este bloco tenta importar o 'financial_bp' e, se falhar, loga um
# erro crítico e encerra a aplicação.
try:
    from routes.financial import financial_bp
except ImportError as e:
    logging.critical(f"FALHA CRÍTICA: O módulo 'financial_bp' não foi encontrado ou contém erros. Verifique 'src/routes/financial.py'. Erro: {e}", exc_info=True)
    sys.exit(1) # Termina a execução com um código de erro

# --- Criação e Configuração da Aplicação Flask ---
app = Flask(__name__)

# Configuração do CORS para produção
# Restringe a permissão de CORS apenas aos endpoints da API que começam com /api/.
# Para máxima segurança, em produção, troque "*" pela URL exata do seu frontend.
# Ex: origins="https://financial-valuation-frontend.onrender.com"
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Registra o blueprint que contém as rotas financeiras.
# Todas as rotas definidas em 'financial_bp' serão prefixadas com '/api/v1'.
# Ex: uma rota '/ranking/full' em financial.py se tornará '/api/v1/ranking/full'.
app.register_blueprint(financial_bp, url_prefix='/api/v1')

@app.route("/")
def index():
    """
    Rota raiz da aplicação. Serve como uma confirmação de que o serviço está no ar,
    mas não é usada para a lógica principal da API.
    """
    return "API do Sistema de Análise Financeira está no ar. Acesse os endpoints em /api/v1/."

# --- Bloco de Execução para Desenvolvimento Local ---
# Este bloco só é executado quando o arquivo é rodado diretamente (ex: `python main.py`).
# Em produção, o servidor Gunicorn importa o objeto 'app' e este bloco é ignorado.
if __name__ == '__main__':
    # Obtém a porta da variável de ambiente, com 5000 como padrão.
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"API iniciando em modo de desenvolvimento em http://0.0.0.0:{port}")
    # O debug=False é mais seguro, mesmo para desenvolvimento local.
    app.run(host='0.0.0.0', port=port, debug=False)
