# backend/src/routes/financial.py

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
import sys
import os
import logging
import traceback
from datetime import datetime

# Adiciona o diretório 'src' ao path do sistema para encontrar os módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ibovespa_analysis_system import IbovespaAnalysisSystem
from utils import clean_data_for_json
# Importa a função específica que será usada neste arquivo
from ibovespa_data import get_market_sectors

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

financial_bp = Blueprint('financial', __name__)

# Singleton pattern para garantir que o sistema de análise seja inicializado apenas uma vez
analysis_system_instance = None
def get_analysis_system():
    """Garante que a instância do sistema de análise seja criada apenas uma vez."""
    global analysis_system_instance
    if analysis_system_instance is None:
        logger.info("Inicializando IbovespaAnalysisSystem...")
        analysis_system_instance = IbovespaAnalysisSystem()
        logger.info("IbovespaAnalysisSystem inicializado com sucesso.")
    return analysis_system_instance

# --- Rotas da API ---

@financial_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Endpoint para verificar a saúde e disponibilidade da API."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

@financial_bp.route('/complete', methods=['POST', 'OPTIONS'])
@cross_origin()
def run_analysis_endpoint():
    """Executa a análise completa ou rápida, recebendo os parâmetros via POST."""
    # O Flask-CORS lida com a requisição preflight OPTIONS automaticamente quando o método é listado.
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        data = request.get_json() if request.data else {}
        num_companies = data.get('num_companies')
        logger.info(f"Recebida requisição de análise. num_companies: {num_companies}")
        
        system = get_analysis_system()
        report = system.run_complete_analysis(num_companies=num_companies)

        if not report or report.get('status') != 'success':
            error_msg = report.get('message', 'Falha ao gerar relatório no sistema.')
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500

        logger.info("Análise concluída e retornada com sucesso.")
        return jsonify(clean_data_for_json(report))

    except Exception as e:
        logger.error(f"Erro catastrófico em /complete: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Um erro interno crítico ocorreu no servidor."}), 500

@financial_bp.route('/company/<string:ticker>', methods=['GET'])
@cross_origin()
def get_company_analysis(ticker):
    """Obtém a análise para uma empresa específica."""
    try:
        logger.info(f"Buscando análise para o ticker: {ticker}")
        system = get_analysis_system()
        result = system.get_company_analysis(ticker.upper())

        if not result or result.get('status') == 'error':
            msg = result.get('message', 'Empresa não encontrada ou dados indisponíveis.')
            return jsonify({"status": "error", "message": msg}), 404

        return jsonify(clean_data_for_json(result))
    except Exception as e:
        logger.error(f"Erro em /company/{ticker}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Erro interno do servidor."}), 500

@financial_bp.route('/companies', methods=['GET'])
@cross_origin()
def get_companies_list():
    """Obtém a lista de empresas do Ibovespa."""
    try:
        system = get_analysis_system()
        companies = system.get_ibovespa_company_list()
        return jsonify({'companies': companies, 'total': len(companies)})
    except Exception as e:
        logger.error(f"Erro em /companies: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Erro ao obter lista de empresas."}), 500

@financial_bp.route('/market/sectors', methods=['GET'])
@cross_origin()
def get_market_sectors_api():
    """Obtém os setores de mercado."""
    try:
        sectors = get_market_sectors()
        return jsonify({'sectors': sectors}), 200
    except Exception as e:
        logger.error(f"Erro ao obter setores de mercado: {e}", exc_info=True)
        return jsonify({'error': 'Erro interno ao carregar setores.'}), 500
