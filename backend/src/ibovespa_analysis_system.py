# backend/src/ibovespa_analysis_system.py

import pandas as pd
import numpy as np
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# Importações de módulos locais
from ibovespa_data import get_ibovespa_tickers, get_selic_rate
from financial_analyzer import FinancialDataCollector, FinancialMetricsCalculator, CompanyRanking
from advanced_ranking import AdvancedRanking, PortfolioOptimizer
from utils import PerformanceMonitor, clean_data_for_json
# --- CORREÇÃO APLICADA AQUI ---
# A classe foi renomeada de 'SupabaseDB' para 'DatabaseManager' para melhor clareza.
# A importação foi atualizada para refletir o nome correto da classe.
from database_manager import DatabaseManager
from financial_analyzer_dataclass import CompanyFinancialData

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class IbovespaAnalysisSystem:
    """
    Sistema de Análise Financeira completo para o Ibovespa.
    Orquestra a coleta de dados, cálculos de métricas e identificação de oportunidades.
    """

    def __init__(self):
        """
        Inicializa todos os componentes necessários para a análise.
        """
        self.monitor = PerformanceMonitor()
        self.collector = FinancialDataCollector()
        
        # Tenta obter a taxa Selic; usa um valor padrão se falhar.
        self.selic_rate = get_selic_rate()
        if self.selic_rate is None:
            logger.warning("Não foi possível obter a taxa Selic. Usando valor padrão de 10%.")
            self.selic_rate = 10.0
            
        # Inicializa as calculadoras e classificadores com a taxa Selic.
        self.calculator = FinancialMetricsCalculator(selic_rate=self.selic_rate)
        self.company_ranking = CompanyRanking(self.calculator)
        self.advanced_ranking = AdvancedRanking(self.calculator)
        self.portfolio_optimizer = PortfolioOptimizer(self.calculator)
        
        # Inicializa o gerenciador de banco de dados.
        self.db = DatabaseManager()

    def run_full_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Executa a análise completa para todas as empresas do Ibovespa.
        Retorna um dicionário contendo o relatório completo.
        """
        self.monitor.start_timer("analise_completa_ibovespa")
        logger.info("Iniciando análise completa do Ibovespa...")

        tickers = get_ibovespa_tickers()
        if not tickers:
            logger.error("Nenhum ticker do Ibovespa encontrado. Abortando análise.")
            return None

        all_companies_data = []
        for ticker in tickers:
            data = self.collector.get_company_financials(ticker)
            if data:
                all_companies_data.append(data)

        if not all_companies_data:
            logger.error("Nenhum dado financeiro pôde ser coletado. Abortando análise.")
            return None

        # Realiza o ranking das empresas
        ranked_companies = self.company_ranking.rank_companies(all_companies_data)
        
        # Prepara o mapa de dados para o otimizador de portfólio
        company_data_map = {data.ticker: data for data in all_companies_data}
        
        # Cria pesos para o portfólio e calcula o EVA agregado
        portfolio_weights = self.portfolio_optimizer.create_score_based_weights(ranked_companies)
        portfolio_eva_abs, portfolio_eva_pct = self.portfolio_optimizer.calculate_portfolio_eva(portfolio_weights, company_data_map)
        
        self.monitor.end_timer("analise_completa_ibovespa")
        
        # Monta o relatório final
        summary = {
            "total_companies_analyzed": len(ranked_companies),
            "positive_eva_count": sum(1 for c in ranked_companies if c['metrics'].get('eva_percentual', 0) > 0),
            "positive_efv_count": sum(1 for c in ranked_companies if c['metrics'].get('efv_percentual', 0) > 0),
            "average_upside": np.nanmean([c['metrics'].get('upside_percentual') for c in ranked_companies if c['metrics'].get('upside_percentual') is not None]),
            "portfolio_eva_abs": portfolio_eva_abs,
            "portfolio_eva_pct": portfolio_eva_pct,
            "execution_time_seconds": self.monitor.timers.get("analise_completa_ibovespa_duration", 0)
        }
        
        report = {
            "report_name": f"Análise Completa Ibovespa - {datetime.now().strftime('%Y-%m-%d')}",
            "report_type": "full",
            "timestamp": datetime.now().isoformat(),
            "summary_statistics": summary,
            "full_ranking_data": ranked_companies,
        }

        return clean_data_for_json(report)

    # Outros métodos da classe podem ser mantidos ou adicionados conforme necessário.
