# backend/main.py

import os
import sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import logging

# Adicionar o diretório 'src' ao sys.path para permitir importações relativas
# Isso é crucial para que os módulos dentro de 'src' possam ser importados corretamente.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from routes.financial import financial_bp
# from models.user import user_bp # Descomente se for usar o blueprint de usuário no futuro
# from models.user import db # Descomente se for usar SQLAlchemy para banco de dados local

# Configurar logging para a aplicação Flask
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instanciar a aplicação Flask
# Definir static_folder para servir os arquivos do frontend após o build
app = Flask(__name__, static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')))

# Configurações do Flask
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_secret_key_here') # Usar variável de ambiente em produção
# Configuração de banco de dados (descomente e adapte se for usar um DB como SQLite ou PostgreSQL com SQLAlchemy)
# app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Habilitar CORS para todas as rotas
# Em produção, considere restringir origins a domínios específicos.
CORS(app)

# Inicializar o banco de dados com a aplicação Flask (descomente se for usar SQLAlchemy)
# db.init_app(app)
# Com app_context, crie as tabelas se não existirem
# with app.app_context():
#     db.create_all()
#     logger.info("Banco de dados inicializado e tabelas criadas (se não existissem).")


# Registrar Blueprints da API
app.register_blueprint(financial_bp, url_prefix='/api/financial')
# app.register_blueprint(user_bp, url_prefix='/api/user') # Descomente se for usar o blueprint de usuário no futuro

# Rota de health check para o deploy (opcional, já temos uma em /api/financial/health)
@app.route('/api/health')
def api_health_check():
    logger.info("Requisição para health check da API recebida.")
    return jsonify({"status": "API healthy", "timestamp": datetime.now().isoformat()}), 200

# Rota para servir os arquivos estáticos do frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """
    Serve os arquivos estáticos do frontend (build do React).
    Se o path for vazio ou não corresponder a um arquivo, serve o index.html.
    """
    logger.debug(f"Tentando servir path: {path} do static_folder: {app.static_folder}")
    if app.static_folder is None:
        logger.error("Static folder not configured for Flask app.")
        return "Static folder not configured", 404

    full_path = os.path.join(app.static_folder, path)
    
    # Se o caminho for um arquivo existente, sirva-o
    if path != "" and os.path.exists(full_path) and os.path.isfile(full_path):
        logger.info(f"Servindo arquivo estático: {path}")
        return send_from_directory(app.static_folder, path)
    # Caso contrário, serve o index.html (SPA fallback)
    else:
        logger.info(f"Servindo index.html para path: {path}")
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Define a porta de execução
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Iniciando a aplicação Flask na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')

