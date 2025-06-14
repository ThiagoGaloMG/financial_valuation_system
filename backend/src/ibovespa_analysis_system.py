# backend/src/ibovespa_analysis_system.py

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ibovespa_data import get_ibovespa_tickers, get_selic_rate
from financial_analyzer import FinancialDataCollector, FinancialMetricsCalculator, CompanyRanking, CompanyFinancialData
from advanced_ranking import AdvancedRanking, PortfolioOptimizer, RankingCriteria
from utils import PerformanceMonitor, clean_data_for_json

# Configurar logging
logging.basicConfig(level=logging.INFO)
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
            self.selic_rate = 10.0 # Valor padrão para Selic se a coleta falhar
        
        self.calculator = FinancialMetricsCalculator(selic_rate=self.selic_rate)
        self.company_ranking = CompanyRanking(self.calculator)
        self.advanced_ranking = AdvancedRanking(self.calculator)
        self.portfolio_optimizer = PortfolioOptimizer(self.calculator)
        
        self.ibovespa_tickers = get_ibovespa_tickers()
        if not self.ibovespa_tickers:
            logger.error("Não foi possível carregar os tickers do Ibovespa. O sistema pode não funcionar corretamente.")
            self.ibovespa_tickers = [] # Garante que é uma lista vazia

    def _get_companies_data(self, tickers: Optional[List[str]] = None) -> Dict[str, CompanyFinancialData]:
        """
        Coleta dados para uma lista específica de tickers ou para todos do Ibovespa.
        """
        if tickers is None:
            tickers_to_process = self.ibovespa_tickers
            logger.info(f"Coletando dados para TODAS as {len(tickers_to_process)} empresas do Ibovespa.")
        else:
            tickers_to_process = tickers
            logger.info(f"Coletando dados para {len(tickers_to_process)} empresas específicas.")

        self.monitor.start_timer("coleta_de_dados")
        companies_data = self.collector.get_multiple_companies(tickers_to_process)
        self.monitor.end_timer("coleta_de_dados")
        
        if not companies_data:
            logger.warning("Nenhum dado de empresa foi coletado com sucesso.")
        return companies_data

    def run_complete_analysis(self, num_companies: Optional[int] = None) -> Dict:
        """
        Executa a análise completa para as empresas do Ibovespa.
        
        Args:
            num_companies (Optional[int]): Limita o número de empresas para análise rápida.
                                          Se None, analisa todas as empresas do Ibovespa.
        
        Returns:
            Dict: Um dicionário contendo o relatório completo da análise, incluindo
                  métricas, rankings e oportunidades.
        """
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
        self.monitor.start_timer("geracao_relatorio_metricas")
        report_df = self.company_ranking.generate_ranking_report(companies_data)
        self.monitor.end_timer("geracao_relatorio_metricas")

        if report_df.empty:
            return {"status": "error", "message": "Relatório de métricas está vazio. Verifique os cálculos."}

        # --- Rankings ---
        logger.info("Gerando rankings...")
        top_10_eva = self.company_ranking.rank_by_eva(report_df)[:10]
        top_10_efv = self.company_ranking.rank_by_efv(report_df)[:10]
        top_10_upside = self.company_ranking.rank_by_upside(report_df)[:10]
        top_10_combined = self.company_ranking.rank_by_combined_score(report_df)[:10]

        # --- Oportunidades Avançadas ---
        logger.info("Identificando oportunidades avançadas e clusters...")
        opportunities = self.advanced_ranking.identify_opportunities(companies_data)

        # --- Sugestão de Portfólio (Exemplo: Moderado) ---
        logger.info("Gerando sugestão de portfólio...")
        portfolio_weights = self.portfolio_optimizer.suggest_portfolio_allocation(companies_data, 'moderate')
        portfolio_eva_abs, portfolio_eva_pct = self.portfolio_optimizer.calculate_portfolio_eva(portfolio_weights, companies_data)

        # --- Estatísticas Resumo ---
        total_companies_analyzed = len(report_df)
        positive_eva_count = (report_df['eva_percentual'] > 0).sum()
        positive_efv_count = (report_df['efv_percentual'] > 0).sum()
        
        avg_eva = report_df['eva_percentual'].mean()
        avg_efv = report_df['efv_percentual'].mean()
        avg_upside = report_df['upside_percentual'].mean()
        
        # Melhor empresa por EVA
        best_eva = report_df.loc[report_df['eva_percentual'].idxmax()] if not report_df['eva_percentual'].empty else {}
        best_efv = report_df.loc[report_df['efv_percentual'].idxmax()] if not report_df['efv_percentual'].empty else {}
        best_combined = report_df.loc[report_df['combined_score'].idxmax()] if not report_df['combined_score'].empty else {}


        # Construir o relatório final
        final_report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_companies_analyzed": total_companies_analyzed,
            "summary_statistics": {
                "positive_eva_count": int(positive_eva_count),
                "positive_efv_count": int(positive_efv_count),
                "avg_eva_percentual": float(avg_eva) if not np.isnan(avg_eva) else None,
                "avg_efv_percentual": float(avg_efv) if not np.isnan(avg_efv) else None,
                "avg_upside_percentual": float(avg_upside) if not np.isnan(avg_upside) else None,
                "best_company_eva": {
                    "ticker": best_eva.get('ticker'),
                    "company_name": best_eva.get('company_name'),
                    "eva_percentual": float(best_eva.get('eva_percentual')) if not pd.isna(best_eva.get('eva_percentual')) else None
                } if not best_eva.empty else {},
                 "best_company_efv": {
                    "ticker": best_efv.get('ticker'),
                    "company_name": best_efv.get('company_name'),
                    "efv_percentual": float(best_efv.get('efv_percentual')) if not pd.isna(best_efv.get('efv_percentual')) else None
                } if not best_efv.empty else {},
                "best_company_combined": {
                    "ticker": best_combined.get('ticker'),
                    "company_name": best_combined.get('company_name'),
                    "combined_score": float(best_combined.get('combined_score')) if not pd.isna(best_combined.get('combined_score')) else None
                } if not best_combined.empty else {},
            },
            "rankings": {
                "top_10_eva": clean_data_for_json([r.to_dict() for _, r in report_df.sort_values(by='eva_percentual', ascending=False).head(10).iterrows()]),
                "top_10_efv": clean_data_for_json([r.to_dict() for _, r in report_df.sort_values(by='efv_percentual', ascending=False).head(10).iterrows()]),
                "top_10_upside": clean_data_for_json([r.to_dict() for _, r in report_df.sort_values(by='upside_percentual', ascending=False).head(10).iterrows()]),
                "top_10_riqueza_atual": clean_data_for_json([r.to_dict() for _, r in report_df.sort_values(by='riqueza_atual', ascending=False).head(10).iterrows()]),
                "top_10_riqueza_futura": clean_data_for_json([r.to_dict() for _, r in report_df.sort_values(by='riqueza_futura', ascending=False).head(10).iterrows()]),
                "top_10_combined": clean_data_for_json([r.to_dict() for _, r in report_df.sort_values(by='combined_score', ascending=False).head(10).iterrows()])
            },
            "opportunities": clean_data_for_json(opportunities),
            "portfolio_suggestion": {
                "weights": clean_data_for_json(portfolio_weights),
                "portfolio_eva_abs": float(portfolio_eva_abs) if not np.isnan(portfolio_eva_abs) else None,
                "portfolio_eva_pct": float(portfolio_eva_pct) if not np.isnan(portfolio_eva_pct) else None
            },
            "full_report_data": clean_data_for_json(report_df.to_dict(orient='records')) # Dados brutos de todas as empresas
        }
        
        self.monitor.end_timer("analise_completa_ibovespa")
        return final_report

    def get_company_analysis(self, ticker: str) -> Dict:
        """
        Realiza a análise de uma empresa específica.
        """
        self.monitor.start_timer(f"analise_empresa_{ticker}")
        company_data = self.collector.get_company_data(ticker)
        
        if not company_data:
            logger.error(f"Não foi possível coletar dados para a empresa {ticker}.")
            return {"status": "error", "message": f"Não foi possível coletar dados para {ticker}"}

        try:
            beta = 1.0 # Exemplo de beta, ajuste para o cálculo do modelo Hamada
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
                    "market_cap": float(company_data.market_cap),
                    "stock_price": float(company_data.stock_price),
                    "wacc_percentual": float(wacc * 100) if not np.isnan(wacc) else None,
                    "eva_abs": float(eva_abs) if not np.isnan(eva_abs) else None,
                    "eva_percentual": float(eva_pct) if not np.isnan(eva_pct) else None,
                    "efv_abs": float(efv_abs) if not np.isnan(efv_abs) else None,
                    "efv_percentual": float(efv_pct) if not np.isnan(efv_pct) else None,
                    "riqueza_atual": float(riqueza_atual) if not np.isnan(riqueza_atual) else None,
                    "riqueza_futura": float(riqueza_futura) if not np.isnan(riqueza_futura) else None,
                    "upside_percentual": float(upside) if not np.isnan(upside) else None,
                    "raw_data": clean_data_for_json(company_data.__dict__) # Inclui todos os dados coletados brutos
                }
            }
            return result
        except Exception as e:
            logger.error(f"Erro ao calcular métricas para {ticker}: {e}")
            return {"status": "error", "message": f"Erro ao processar dados para {ticker}: {str(e)}"}
        finally:
            self.monitor.end_timer(f"analise_empresa_{ticker}")

    def get_ibovespa_company_list(self) -> List[Dict]:
        """Retorna a lista de empresas do Ibovespa com tickers formatados."""
        return [{"ticker": t, "ticker_clean": t.replace(".SA", "")} for t in self.ibovespa_tickers]

if __name__ == '__main__':
    # Exemplo de uso do sistema completo
    print("Iniciando demonstração do IbovespaAnalysisSystem...")
    system = IbovespaAnalysisSystem()

    # Rodar análise rápida (ex: 5 empresas)
    print("\n--- Análise Rápida (5 Empresas) ---")
    quick_report = system.run_complete_analysis(num_companies=5)
    print(json.dumps(quick_report, indent=2, ensure_ascii=False))

    # Rodar análise completa (para todas as empresas, pode demorar!)
    # print("\n--- Análise Completa (Todas as Empresas) ---")
    # full_report = system.run_complete_analysis()
    # print(json.dumps(full_report, indent=2, ensure_ascii=False))

    # Análise de uma empresa específica
    print("\n--- Análise de Empresa Específica (PETR4.SA) ---")
    petr4_analysis = system.get_company_analysis("PETR4.SA")
    print(json.dumps(petr4_analysis, indent=2, ensure_ascii=False))
