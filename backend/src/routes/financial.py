# backend/src/routes/financial.py

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import sys
import os
import logging
import traceback
from datetime import datetime
import json

# Adicionar o diretório src ao path para importar os módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ibovespa_analysis_system import IbovespaAnalysisSystem
from utils import clean_data_for_json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint para as rotas financeiras
financial_bp = Blueprint('financial', __name__)

# Instância global do sistema de análise (inicializada uma vez)
analysis_system_instance = None

def get_analysis_system():
    """
    Função para obter a instância (singleton) do sistema de análise.
    """
    global analysis_system_instance
    if analysis_system_instance is None:
        logger.info("Inicializando IbovespaAnalysisSystem pela primeira vez...")
        analysis_system_instance = IbovespaAnalysisSystem()
        logger.info("IbovespaAnalysisSystem inicializado.")
    return analysis_system_instance

@financial_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """
    Endpoint para verificar se a API está funcionando.
    """
    try:
        system = get_analysis_system()
        status = {
            'status': 'healthy',
            'message': 'API de Análise Financeira está funcionando',
            'timestamp': datetime.now().isoformat(),
            'system_initialized': system is not None
        }
        logger.info("Health check realizado com sucesso.")
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Erro no health check: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@financial_bp.route('/complete', methods=['POST']) # ROTA CORRIGIDA
@cross_origin()
def run_complete_analysis():
    """
    Executa a análise completa ou rápida.
    """
    try:
        logger.info("Iniciando análise completa/rápida via API")
        
        system = get_analysis_system()
        
        data = request.get_json(silent=True)
        num_companies = None
        if data and 'num_companies' in data:
            num_companies = data.get('num_companies')
        
        start_time = datetime.now()
        report = system.run_complete_analysis(num_companies=num_companies)
        end_time = datetime.now()
        
        report['execution_time_seconds'] = (end_time - start_time).total_seconds()
        
        cleaned_report = clean_data_for_json(report)
        
        logger.info("Análise finalizada via API.")
        return jsonify(cleaned_report), 200
        
    except Exception as e:
        logger.error(f"Erro ao executar análise: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': 'Erro interno do servidor ao executar análise',
            'error_details': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@financial_bp.route('/company/<ticker>', methods=['GET']) # ROTA CORRIGIDA
@cross_origin()
def get_company_analysis(ticker):
    """
    Obtém a análise para uma empresa específica.
    """
    try:
        logger.info(f"Iniciando análise para empresa específica: {ticker}")
        
        system = get_analysis_system()
        analysis_result = system.get_company_analysis(ticker.upper())
        
        cleaned_result = clean_data_for_json(analysis_result)
        
        logger.info(f"Análise para {ticker} finalizada.")
        return jsonify(cleaned_result), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter dados para {ticker}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Erro interno do servidor ao obter dados para {ticker}',
            'error_details': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@financial_bp.route('/companies', methods=['GET'])
@cross_origin()
def get_companies_list():
    """
    Obtém a lista de empresas do Ibovespa.
    """
    try:
        logger.info("Obtendo lista de empresas do Ibovespa.")
        system = get_analysis_system()
        
        companies = system.get_ibovespa_company_list()
        
        result = {
            'companies': companies,
            'total': len(companies),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Lista de empresas retornada: {len(companies)} empresas.")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter lista de empresas: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'error': 'Erro interno do servidor ao obter lista de empresas',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
