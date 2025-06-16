# backend/src/routes/financial.py

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
import sys
import os
import logging
import traceback
from datetime import datetime

# Garante que os módulos do diretório 'src' possam ser importados
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ibovespa_analysis_system import IbovespaAnalysisSystem
from utils import clean_data_for_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

financial_bp = Blueprint('financial', __name__)
analysis_system_instance = None

def get_analysis_system():
    """Garante que a instância do sistema de análise seja criada apenas uma vez (padrão Singleton)."""
    global analysis_system_instance
    if analysis_system_instance is None:
        logger.info("Inicializando IbovespaAnalysisSystem...")
        analysis_system_instance = IbovespaAnalysisSystem()
        logger.info("IbovespaAnalysisSystem inicializado com sucesso.")
    return analysis_system_instance

@financial_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Endpoint para verificar a saúde e disponibilidade da API."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

# ==========================================================================================
# ROTA CORRIGIDA: Aceita POST (para os dados) e OPTIONS (para o CORS preflight)
# ==========================================================================================
@financial_bp.route('/complete', methods=['POST', 'OPTIONS'])
@cross_origin()
def run_analysis_endpoint():
    """Executa a análise completa ou rápida, recebendo os parâmetros via POST."""
    # O Flask-CORS lida com a requisição OPTIONS automaticamente.
    # A lógica abaixo só será executada para a requisição POST.
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
        logger.error(f"Erro catastrófico em /complete: {e}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": "Um erro interno crítico ocorreu no servidor."}), 500

# ==========================================================================================
# ROTA CORRIGIDA: Removido o prefixo '/analyze' para corresponder à chamada do frontend.
# ==========================================================================================
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
        logger.error(f"Erro em /company/{ticker}: {e}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": "Erro interno do servidor."}), 500
