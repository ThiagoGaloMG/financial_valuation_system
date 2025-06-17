# backend/main.py
import os
import sys
from flask import Flask
from flask_cors import CORS
import logging

# Adiciona o diretório 'src' ao path do sistema para encontrar os módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from routes.financial import financial_bp
except ImportError as e:
    logging.critical(f"FALHA CRÍTICA: Não foi possível importar 'financial_bp'. Erro: {e}")
    raise

# Configuração do Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Cria a aplicação Flask
app = Flask(__name__)

# Habilita CORS para permitir a comunicação com o frontend
CORS(app)

# --- CORREÇÃO PRINCIPAL ---
# O prefixo da URL foi corrigido para corresponder ao que o frontend espera.
app.register_blueprint(financial_bp, url_prefix='/api/v1')

@app.route("/")
def index():
    """Rota raiz para confirmar que a API está online."""
    return "API do Sistema de Análise Financeira está no ar."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logging.info(f"Iniciando servidor de desenvolvimento em http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
