# backend/src/ibovespa_analysis_system.py

import pandas as pd
import numpy as np
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from ibovespa_data import get_ibovespa_tickers, get_selic_rate
from financial_analyzer import FinancialDataCollector, FinancialMetricsCalculator, CompanyRanking
from advanced_ranking import AdvancedRanking, PortfolioOptimizer
from utils import PerformanceMonitor, clean_data_for_json
from database_manager import SupabaseDB
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
        
        # Carregar tickers do Ibovespa
        self.ibovespa_tickers = get_ibovespa_tickers()
        if not self.ibovespa_tickers:
            logger.error("Não foi possível carregar os tickers do Ibovespa. A aplicação pode não funcionar como esperado.")
            self.ibovespa_tickers = []
        
        # Inicializar conexão com banco
        try:
            self.db = SupabaseDB()
        except Exception as e:
            logger.error(f"Falha ao inicializar SupabaseDB: {e}")
            self.db = None

    def _get_companies_data(self, tickers: Optional[List[str]] = None) -> Dict[str, CompanyFinancialData]:
        """
        Coleta dados históricos e atuais para uma lista de tickers.
        Usa FinancialDataCollector que implementa retry e fallback.
        """
        tickers_to_process = tickers if tickers is not None else self.ibovespa_tickers
        logger.info(f"Iniciando coleta de dados para {len(tickers_to_process)} tickers.")
        # Coleta em lote com delays internos se necessário
        companies_data = self.collector.get_multiple_companies(tickers_to_process)
        return companies_data

    def run_complete_analysis(self, num_companies: Optional[int] = None) -> Dict:
        """Executa a análise completa ou rápida para as empresas do Ibovespa."""
        self.monitor.start_timer("analise_completa_ibovespa")
        
        # Definir tickers para análise rápida ou completa
        tickers_to_use = self.ibovespa_tickers
        if num_companies is not None and 0 < num_companies < len(self.ibovespa_tickers):
            tickers_to_use = self.ibovespa_tickers[:num_companies]
            logger.info(f"Executando análise rápida para as primeiras {num_companies} empresas.")
        else:
            logger.info(f"Executando análise completa para {len(tickers_to_use)} empresas do Ibovespa.")

        # Coleta dados
        companies_data = self._get_companies_data(tickers=tickers_to_use)
        if not companies_data:
            self.monitor.end_timer("analise_completa_ibovespa")
            return {"status": "error", "message": "Nenhum dado foi coletado para a análise."}

        # Gera relatório de métricas via CompanyRanking
        logger.info("Gerando relatório de métricas para todas as empresas...")
        report_df = self.company_ranking.generate_ranking_report(companies_data)
        if report_df is None or report_df.empty:
            self.monitor.end_timer("analise_completa_ibovespa")
            return {"status": "error", "message": "O relatório de métricas está vazio."}

        # Persistir métricas individuais no banco de dados, se disponível
        if self.db:
            for ticker, company_data_obj in companies_data.items():
                try:
                    # Obtém linha de métricas para ticker
                    row = report_df[report_df['ticker'] == ticker]
                    if row.empty:
                        continue
                    metrics_for_db = row.iloc[0].to_dict()
                    # Adiciona raw_data se disponível
                    raw = vars(company_data_obj)
                    metrics_for_db['raw_data'] = clean_data_for_json(raw)
                    # Salva via SupabaseDB
                    self.db.save_company_metrics(company_data_obj, metrics_for_db)
                    logger.info(f"Métricas para {ticker} salvas no DB.")
                except Exception as e:
                    logger.error(f"Erro ao persistir métricas para {ticker}: {e}")

        # Análises avançadas (opportunities, clusters, etc.)
        try:
            opportunities = self.advanced_ranking.identify_opportunities(companies_data)
        except Exception as e:
            logger.error(f"Erro em advanced_ranking.identify_opportunities: {e}")
            opportunities = []

        final_report = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_companies_analyzed": len(report_df),
            "summary_statistics": {
                # Ajuste campos conforme colunas de report_df
                "positive_eva_count": int((report_df.get('eva_percentual', pd.Series()) > 0).sum()) if 'eva_percentual' in report_df.columns else 0,
                "positive_efv_count": int((report_df.get('efv_percentual', pd.Series()) > 0).sum()) if 'efv_percentual' in report_df.columns else 0,
            },
            "opportunities": opportunities,
            "full_report_data": report_df.to_dict(orient='records')
        }
        
        self.monitor.end_timer("analise_completa_ibovespa")
        return clean_data_for_json(final_report)

    def get_company_analysis(self, ticker: str) -> Dict:
        """Realiza a análise de uma empresa específica."""
        self.monitor.start_timer(f"analise_empresa_{ticker}")
        ticker = ticker.upper().strip()
        # Coleta dados da empresa
        try:
            company_data = self.collector.get_company_data(ticker)
        except Exception as e:
            logger.error(f"Erro ao coletar dados para {ticker}: {e}")
            self.monitor.end_timer(f"analise_empresa_{ticker}")
            return {"status": "error", "message": f"Não foi possível coletar dados para {ticker}"}

        if not company_data:
            logger.error(f"Dados não encontrados para {ticker}.")
            self.monitor.end_timer(f"analise_empresa_{ticker}")
            return {"status": "error", "message": f"Não foi possível coletar dados para {ticker}"}

        # Tenta buscar dados persistidos se houver DB
        if self.db:
            try:
                persisted = self.db.get_latest_company_metrics(ticker)
                if persisted:
                    logger.info(f"Retornando dados persistidos para {ticker}.")
                    self.monitor.end_timer(f"analise_empresa_{ticker}")
                    return clean_data_for_json(persisted)
            except Exception as e:
                logger.error(f"Erro ao buscar dados persistidos para {ticker}: {e}")

        # Cálculos dinâmicos via FinancialMetricsCalculator
        try:
            # Exemplo de uso: calcula WACC, EVA, EFV, riqueza, upside
            beta = 1.0  # ou calculado
            wacc = self.calculator._calculate_wacc(company_data, beta)
            eva_abs, eva_pct = self.calculator.calculate_eva(company_data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(company_data, beta)
            riqueza_atual = self.calculator.calculate_riqueza_atual(company_data, beta)
            riqueza_futura = self.calculator.calculate_riqueza_futura(company_data)
            upside = self.calculator.calculate_upside(company_data, efv_abs) if not np.isnan(efv_abs) else None

            result = {
                "status": "success",
                "ticker": ticker,
                "company_name": company_data.company_name,
                "metrics": {
                    "market_cap": company_data.market_cap,
                    "stock_price": company_data.stock_price,
                    "wacc_percentual": (wacc * 100) if wacc is not None else None,
                    "eva_abs": eva_abs,
                    "eva_percentual": eva_pct,
                    "efv_abs": efv_abs,
                    "efv_percentual": efv_pct,
                    "riqueza_atual": riqueza_atual,
                    "riqueza_futura": riqueza_futura,
                    "upside_percentual": upside
                }
            }
        except Exception as e:
            logger.error(f"Erro ao calcular métricas para {ticker}: {e}")
            result = {"status": "error", "message": f"Erro ao processar dados para {ticker}: {str(e)}"}

        # Persistir resultado dinâmico, se desejado
        if self.db and result.get('status') == 'success':
            try:
                metrics_for_db = result['metrics'].copy()
                raw = vars(company_data)
                metrics_for_db['raw_data'] = clean_data_for_json(raw)
                self.db.save_company_metrics(company_data, metrics_for_db)
                logger.info(f"Métricas dinâmicas para {ticker} salvas no DB.")
            except Exception as e:
                logger.error(f"Erro ao persistir métricas dinâmicas para {ticker}: {e}")

        self.monitor.end_timer(f"analise_empresa_{ticker}")
        return clean_data_for_json(result)

    def get_ibovespa_company_list(self) -> List[Dict]:
        """Retorna a lista de empresas do Ibovespa com tickers formatados."""
        return [{"ticker": t, "ticker_clean": t.replace(".SA", "")} for t in self.ibovespa_tickers]
