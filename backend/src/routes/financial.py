# backend/src/routes/financial.py

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
import sys
import os
import logging
import traceback
from datetime import datetime
import json  # Para converter dados em JSON ao inserir no banco
import psycopg2
from psycopg2.extras import RealDictCursor

# Adiciona o diretório 'src' ao path do sistema para encontrar módulos internos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ibovespa_analysis_system import IbovespaAnalysisSystem
from utils import clean_data_for_json

# Import para integração com Supabase (psycopg2) e funções de persistência
try:
    from db.database import (
        insert_analysis_report,
        get_or_create_company,
        insert_or_update_financial_metrics,
        get_connection
    )
except ImportError as e:
    logging.warning(f"Não foi possível importar funções de persistência: {e}. Persistência ficará inativa.")
    insert_analysis_report = None
    get_or_create_company = None
    insert_or_update_financial_metrics = None
    get_connection = None

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

financial_bp = Blueprint('financial', __name__)

# --- Health Check (apenas uma definição) ---
@financial_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Endpoint para verificar se a API está rodando."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

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

@financial_bp.route('/complete', methods=['POST', 'OPTIONS'])
@cross_origin()
def run_analysis_endpoint():
    """Executa a análise completa ou rápida, recebendo os parâmetros via POST."""
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

        logger.info("Análise concluída com sucesso. Iniciando persistência no banco de dados (se disponível)...")

        errors_persist = []
        # Persistir empresas e métricas, se as funções estiverem disponíveis
        if get_or_create_company and insert_or_update_financial_metrics:
            # Extrair timestamp do report como datetime
            timestamp_str = report.get("timestamp")
            try:
                if timestamp_str:
                    iso = timestamp_str
                    if iso.endswith("Z"):
                        iso = iso.replace("Z", "+00:00")
                    analysis_date = datetime.fromisoformat(iso)
                else:
                    analysis_date = datetime.now()
            except Exception:
                analysis_date = datetime.now()

            full_data = report.get("full_report_data", [])
            for item in full_data:
                try:
                    # Obter ticker (adapte se a chave for diferente)
                    ticker = item.get("ticker") or item.get("symbol")
                    if not ticker:
                        raise ValueError("Ticker ausente no item de relatório")
                    ticker = ticker.upper().strip()
                    # Nome e setor, se disponíveis
                    company_name = item.get("company_name") or item.get("name") or ticker
                    sector = item.get("sector")  # pode ser None
                    # 1) obter ou criar empresa
                    company_id = get_or_create_company(ticker, company_name, sector)
                    # 2) extrair métricas: adapte conforme a estrutura real
                    # Supondo que o dicionário de métricas esteja em item["metrics"] ou item["metricas"]
                    metrics = item.get("metrics") or item.get("metricas") or {}
                    if not isinstance(metrics, dict):
                        raise ValueError(f"Estrutura de métricas inesperada para {ticker}: {type(metrics)}")
                    # 3) raw_data, se disponível (para auditoria)
                    raw_data = item.get("raw_data", None)
                    # 4) inserir ou atualizar métricas
                    insert_or_update_financial_metrics(company_id, analysis_date, metrics, raw_data)
                    logger.info(f"Métricas para {ticker} salvas com sucesso.")
                except Exception as e_item:
                    msg = f"Erro ao persistir dados de {item.get('ticker')}: {e_item}"
                    logger.error(msg, exc_info=True)
                    errors_persist.append(msg)
        else:
            logger.warning("Funções de persistência de empresas e métricas não disponíveis; pulando essa etapa.")

        # Persistir relatório agregado
        if insert_analysis_report:
            try:
                insert_analysis_report(report)
                logger.info("Relatório agregado persistido com sucesso.")
            except Exception as e_report:
                logger.error(f"Falha ao persistir relatório agregado: {e_report}", exc_info=True)
                errors_persist.append(f"Relatório: {e_report}")
        else:
            logger.warning("Função insert_analysis_report não disponível; pulando persistência de relatório agregado.")

        if errors_persist:
            logger.warning(f"Ocorreram erros na persistência: {errors_persist}")

        # Retorna o report ao frontend
        return jsonify(clean_data_for_json(report))

    except Exception as e:
        logger.error(f"Erro catastrófico em /complete: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Um erro interno crítico ocorreu no servidor."}), 500

@financial_bp.route('/company/<string:ticker>', methods=['GET'])
@cross_origin()
def get_company_analysis(ticker):
    """Obtém a análise para uma empresa específica, preferindo dados persistidos."""
    try:
        ticker = ticker.upper().strip()
        logger.info(f"Buscando análise para o ticker: {ticker}")

        # Se persistência disponível, tenta buscar no banco primeiro
        if get_connection:
            try:
                conn = get_connection()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                # 1) buscar empresa
                cur.execute("SELECT id, company_name, sector FROM public.companies WHERE ticker = %s;", (ticker,))
                company = cur.fetchone()
                if company:
                    company_id = company['id']
                    # 2) buscar métrica mais recente
                    cur.execute("""
                        SELECT * FROM public.financial_metrics
                        WHERE company_id = %s
                        ORDER BY analysis_date DESC
                        LIMIT 1;
                    """, (company_id,))
                    metric = cur.fetchone()
                    cur.close()
                    conn.close()
                    if metric:
                        # Monta resposta baseada em dados salvos
                        response = {
                            "status": "success",
                            "ticker": ticker,
                            "company_name": company.get('company_name'),
                            "sector": company.get('sector'),
                            "metrics": {
                                "market_cap": metric.get("market_cap"),
                                "stock_price": metric.get("stock_price"),
                                "wacc_percentual": metric.get("wacc_percentual"),
                                "eva_abs": metric.get("eva_abs"),
                                "eva_percentual": metric.get("eva_percentual"),
                                "efv_abs": metric.get("efv_abs"),
                                "efv_percentual": metric.get("efv_percentual"),
                                "riqueza_atual": metric.get("riqueza_atual"),
                                "riqueza_futura": metric.get("riqueza_futura"),
                                "upside_percentual": metric.get("upside_percentual"),
                                "combined_score": metric.get("combined_score"),
                            },
                            "analysis_date": metric.get("analysis_date").isoformat()
                        }
                        return jsonify(response)
                # Se não encontrou dados, cai para recálculo
                logger.info(f"Dados persistidos não encontrados para {ticker}. Realizando recálculo dinâmico.")
            except Exception as e_db:
                logger.error(f"Erro ao buscar dados persistidos para {ticker}: {e_db}", exc_info=True)
                # continua para recálculo dinâmico

        # Recálculo dinâmico via sistema original
        try:
            system = get_analysis_system()
            result = system.get_company_analysis(ticker)
            # Opcional: persistir resultado recém-calculado, similar a /complete
            return jsonify(clean_data_for_json(result))
        except Exception as e_sys:
            logger.error(f"Erro em recálculo dinâmico para /company/{ticker}: {e_sys}", exc_info=True)
            return jsonify({"status": "error", "message": "Erro interno do servidor."}), 500

@financial_bp.route('/companies', methods=['GET'])
@cross_origin()
def get_companies_list():
    """Obtém a lista de empresas do Ibovespa via sistema original."""
    try:
        system = get_analysis_system()
        companies = system.get_ibovespa_company_list()
        return jsonify({'companies': companies, 'total': len(companies)})
    except Exception as e:
        logger.error(f"Erro em /companies: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Erro ao obter lista de empresas."}), 500

@financial_bp.route('/saved_companies', methods=['GET'])
@cross_origin()
def get_saved_companies():
    """Retorna empresas já salvas no banco."""
    if not get_connection:
        return jsonify({"status": "error", "message": "Persistência não configurada."}), 500
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, ticker, company_name, sector, last_updated FROM public.companies ORDER BY ticker;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({'companies': rows}), 200
    except Exception as e:
        logger.error(f"Erro em get_saved_companies: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Erro ao obter empresas salvas."}), 500

# Você pode adicionar outros endpoints, como listar analysis_reports ou métricas históricas, conforme necessidade.
