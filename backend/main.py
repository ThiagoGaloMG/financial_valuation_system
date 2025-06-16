# backend/main.py

import os
import sys
from flask import Flask
from flask_cors import CORS
import logging

# Adicionar o diretório 'src' ao sys.path para permitir importações de módulos.
# Ex: from routes.financial import financial_bp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    # Importar o blueprint APÓS a modificação do path
    from routes.financial import financial_bp
except ImportError as e:
    logging.critical(f"Falha ao importar o blueprint financeiro. Verifique o sys.path e a estrutura de pastas. Erro: {e}")
    raise

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Instanciar a aplicação Flask
app = Flask(__name__)

# Habilitar CORS para permitir que o frontend se comunique com esta API.
CORS(app)

# =====================================================================================
# CORREÇÃO DEFINITIVA AQUI:
# O url_prefix foi corrigido de '/api/financial' para '/api/v1'.
# Agora as rotas do seu 'financial.py' (ex: /complete) serão acessíveis em
# /api/v1/complete, que é o que o frontend está chamando.
# =====================================================================================
app.register_blueprint(financial_bp, url_prefix='/api/v1')

@app.route("/")
def index():
    """ Rota raiz para confirmar que a API está no ar. """
    logging.info("Rota raiz acessada.")
    return "API do Sistema de Análise Financeira está no ar."

if __name__ == '__main__':
    # Esta seção só é executada quando você roda o script diretamente (python main.py),
    # não quando o Gunicorn o importa em produção.
    port = int(os.environ.get('PORT', 5001))
    logging.info(f"Iniciando servidor de desenvolvimento na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
