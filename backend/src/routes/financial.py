# backend/src/routes/financial.py
# Este arquivo define os endpoints (rotas) da API Flask.
# Atua como a camada controladora, recebendo requisições web e orquestrando
# as respostas ao chamar os módulos de lógica de negócio e persistência.

import logging
import os
import sys
from flask import Blueprint, jsonify
from flask_cors import cross_origin

# Adiciona o diretório 'src' ao path do sistema para permitir importações locais.
# Ex: from database_manager import DatabaseManager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa as classes principais que contêm a lógica da aplicação.
from database_manager import DatabaseManager
from ibovespa_analysis_system import IbovespaAnalysisSystem

# Configuração do logger para este módulo.
logger = logging.getLogger(__name__)

# Cria um 'Blueprint' do Flask. Blueprints são usados para organizar uma aplicação Flask
# em componentes distintos e reutilizáveis.
financial_bp = Blueprint('financial', __name__)

# Define o "Tempo de Vida" (Time to Live) do cache em horas.
# Relatórios no banco de dados com mais de 12 horas serão considerados obsoletos,
# e uma nova análise será executada.
CACHE_TTL_HOURS = 12

@financial_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """
    Endpoint de verificação de saúde (Health Check).
    O Render usa esta rota para verificar se a aplicação está no ar e respondendo.
    Retorna um status 'ok' simples.
    """
    return jsonify({"status": "ok"})

@financial_bp.route('/ranking/full', methods=['GET'])
@cross_origin()
def get_full_ibovespa_ranking():
    """
    Endpoint principal para obter o ranking completo e analisado das empresas do Ibovespa.
    
    Implementa uma lógica de cache inteligente para otimizar a performance:
    1.  Tenta buscar um relatório recente (com menos de CACHE_TTL_HOURS) do Supabase.
    2.  Se um relatório recente for encontrado no cache, ele é retornado imediatamente.
    3.  Se não houver um relatório recente, o sistema executa uma nova análise completa,
        que envolve a coleta de dados via yfinance e todos os cálculos financeiros.
    4.  O novo relatório é então salvo no banco de dados para servir como cache para
        futuras requisições.
    5.  O novo relatório é retornado ao cliente.
    """
    db_manager = DatabaseManager()

    # 1. Tenta buscar um resultado do cache do banco de dados.
    try:
        cached_report = db_manager.get_latest_analysis_report(max_age_hours=CACHE_TTL_HOURS)
        if cached_report:
            # Se encontrou um relatório recente, retorna-o imediatamente.
            return jsonify(cached_report)
    except Exception as e:
        # Se houver um erro ao acessar o DB, registra o erro mas continua
        # para a análise ao vivo, garantindo a resiliência da API.
        logger.error(f"Erro ao acessar o cache do DB. Prosseguindo com análise ao vivo: {e}", exc_info=True)

    # 2. Se não houver cache, executa uma nova análise completa.
    logger.info("Nenhum relatório recente no cache. Iniciando nova análise completa do Ibovespa...")
    try:
        # Instancia o sistema principal que orquestra a análise.
        system = IbovespaAnalysisSystem()
        # Executa a análise, que pode levar algum tempo.
        full_report_data = system.run_full_analysis()

        if not full_report_data:
            logger.error("A análise completa foi executada mas não retornou dados.")
            return jsonify({"status": "error", "message": "A análise não retornou dados de ranking."}), 500

        # 3. Salva o novo resultado no banco de dados para atuar como cache.
        try:
            db_manager.save_analysis_report(full_report_data)
        except Exception as e:
            # Se o salvamento no DB falhar, a aplicação ainda deve retornar os dados ao usuário.
            # Apenas registra o erro para depuração.
            logger.error(f"Análise concluída, mas falhou ao salvar o novo relatório no cache: {e}", exc_info=True)

        logger.info("Análise completa do Ibovespa concluída e retornada com sucesso.")
        return jsonify(full_report_data)

    except Exception as e:
        # Captura qualquer erro crítico que possa ocorrer durante a execução da análise.
        logger.critical(f"Erro CRÍTICO e inesperado ao gerar o ranking completo: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Um erro interno crítico ocorreu no servidor ao processar a análise."}), 500
