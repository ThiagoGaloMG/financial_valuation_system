# backend/src/ibovespa_analysis_system.py

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ibovespa_data import get_ibovespa_tickers, get_selic_rate
from financial_analyzer import FinancialDataCollector, FinancialMetricsCalculator, CompanyRanking
from advanced_ranking import AdvancedRanking, PortfolioOptimizer
from utils import PerformanceMonitor, clean_data_for_json
from database_manager import SupabaseDB

# --- CORREÇÃO PRINCIPAL ---
# A classe CompanyFinancialData agora é importada do seu próprio arquivo dedicado
# para resolver a dependência circular.
from financial_analyzer_dataclass import CompanyFinancialData


# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class IbovespaAnalysisSystem:
    """
    Sistema de Análise Financeira completo para o Ibovespa.
    Orquestra a coleta de dados, cálculos de métricas (EVA, EFV, Riqueza),
    classificação de empresas e identificação de oportunidades.
    """

    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.collector = FinancialDataCollector()
        self.selic_rate = get_selic_rate()
        if self.selic_rate is None:
            logger.warning("Não foi possível obter a taxa Selic. Usando valor padrão de 10%.")
            self.selic_rate = 10.0
        
        self.calculator = FinancialMetricsCalculator(selic_rate=self.selic_rate)
        self.company_ranking = CompanyRanking(self.calculator)
        self.advanced_ranking = AdvancedRanking(self.calculator)
        self.portfolio_optimizer = PortfolioOptimizer(self.calculator)
        
        self.ibovespa_tickers = get_ibovespa_tickers()
        if not self.ibovespa_tickers:
            logger.error("Não foi possível carregar os tickers do Ibovespa. A aplicação pode não funcionar como esperado.")
            self.ibovespa_tickers = []

        self.db = SupabaseDB()

    def _get_companies_data(self, tickers: Optional[List[str]] = None) -> Dict[str, CompanyFinancialData]:
        """Coleta dados para uma lista de tickers, usando o banco de dados como cache."""
        tickers_to_process = tickers if tickers is not None else self.ibovespa_tickers
        
        companies_data = {}
        for ticker in tickers_to_process:
            # Lógica para usar dados do DB se forem recentes foi removida para simplificar
            # e focar no fluxo principal de coleta e fallback.
            # Em uma versão futura, a lógica de cache pode ser reintroduzida aqui.
            logger.info(f"Coletando dados para {ticker}.")
            self.monitor.start_timer(f"coleta_yfinance_{ticker}")
            data = self.collector.get_company_data(ticker)
            self.monitor.end_timer(f"coleta_yfinance_{ticker}")
            if data:
                companies_data[ticker] = data
            else:
                logger.warning(f"Não foi possível coletar dados para {ticker}.")
        return companies_data

    def run_complete_analysis(self, num_companies: Optional[int] = None) -> Dict:
        """Executa a análise completa para as empresas do Ibovespa."""
        self.monitor.start_timer("analise_completa_ibovespa")
        
        tickers_to_use = self.ibovespa_tickers
        if num_companies is not None and num_companies > 0:
            tickers_to_use = self.ibovespa_tickers[:num_companies]
            logger.info(f"Executando análise rápida para as primeiras {num_companies} empresas.")
        else:
            logger.info(f"Executando análise completa para {len(tickers_to_use)} empresas do Ibovespa.")

        companies_data = self._get_companies_data(tickers=tickers_to_use)

        if not companies_data:
            return {"status": "error", "message": "Nenhum dado coletado para análise."}

        # Gerar o DataFrame com todas as métricas calculadas
        logger.info("Gerando relatório de métricas para todas as empresas...")
        report_df = self.company_ranking.generate_ranking_report(companies_data)

        if report_df.empty:
            return {"status": "error", "message": "Relatório de métricas está vazio."}

        # Salvar métricas individuais no DB
        for ticker_key, company_data_obj in companies_data.items():
            if not report_df[report_df['ticker'] == ticker_key].empty:
                metrics_for_db = report_df[report_df['ticker'] == ticker_key].iloc[0].to_dict()
                metrics_for_db['raw_data'] = clean_data_for_json(vars(company_data_obj))
                self.db.save_company_metrics(company_data_obj, metrics_for_db)

        # Rankings e Oportunidades
        opportunities = self.advanced_ranking.identify_opportunities(companies_data)
        portfolio_weights = self.portfolio_optimizer.suggest_portfolio_allocation(companies_data, 'moderate')
        portfolio_eva_abs, portfolio_eva_pct = self.portfolio_optimizer.calculate_portfolio_eva(portfolio_weights, companies_data)

        # Construir o relatório final
        final_report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_companies_analyzed": len(report_df),
            "summary_statistics": {
                "positive_eva_count": int((report_df['eva_percentual'] > 0).sum()),
                "positive_efv_count": int((report_df['efv_percentual'] > 0).sum()),
            },
            "rankings": {
                "top_10_combined": report_df.sort_values(by='combined_score', ascending=False).head(10).to_dict(orient='records')
            },
            "opportunities": opportunities,
            "portfolio_suggestion": {
                "weights": portfolio_weights,
                "portfolio_eva_abs": portfolio_eva_abs,
                "portfolio_eva_pct": portfolio_eva_pct
            },
            "full_report_data": report_df.to_dict(orient='records')
        }
        
        self.monitor.end_timer("analise_completa_ibovespa")
        return clean_data_for_json(final_report)

    def get_company_analysis(self, ticker: str) -> Dict:
        """Realiza a análise de uma empresa específica."""
        self.monitor.start_timer(f"analise_empresa_{ticker}")
        
        company_data = self.collector.get_company_data(ticker)
        
        if not company_data:
            logger.error(f"Não foi possível coletar dados para a empresa {ticker}.")
            return {"status": "error", "message": f"Não foi possível coletar dados para {ticker}"}

        try:
            beta = 1.0 
            wacc = self.calculator._calculate_wacc(company_data, beta)
            eva_abs, eva_pct = self.calculator.calculate_eva(company_data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(company_data, beta)
            riqueza_atual = self.calculator.calculate_riqueza_atual(company_data, beta)
            riqueza_futura = self.calculator.calculate_riqueza_futura(company_data)
            upside = self.calculator.calculate_upside(company_data, efv_abs) if not np.isnan(efv_abs) else np.nan
            
            result = {
                "status": "success",
                "ticker": company_data.ticker,
                "company_name": company_data.company_name,
                "metrics": {
                    "market_cap": company_data.market_cap,
                    "stock_price": company_data.stock_price,
                    "wacc_percentual": wacc * 100 if not np.isnan(wacc) else None,
                    "eva_abs": eva_abs, "eva_percentual": eva_pct,
                    "efv_abs": efv_abs, "efv_percentual": efv_pct,
                    "riqueza_atual": riqueza_atual, "riqueza_futura": riqueza_futura,
                    "upside_percentual": upside
                }
            }
            return clean_data_for_json(result)
        except Exception as e:
            logger.error(f"Erro ao calcular métricas para {ticker}: {e}")
            return {"status": "error", "message": f"Erro ao processar dados para {ticker}: {str(e)}"}
        finally:
            self.monitor.end_timer(f"analise_empresa_{ticker}")

    def get_ibovespa_company_list(self) -> List[Dict]:
        """Retorna a lista de empresas do Ibovespa com tickers formatados."""
        return [{"ticker": t, "ticker_clean": t.replace(".SA", "")} for t in self.ibovespa_tickers]
