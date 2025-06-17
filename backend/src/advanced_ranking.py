# backend/src/advanced_ranking.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import warnings

# --- CORREÇÃO PRINCIPAL ---
# A importação da classe CompanyFinancialData foi movida para o novo arquivo dedicado,
# enquanto as outras classes continuam vindo do financial_analyzer.
from financial_analyzer import FinancialMetricsCalculator
from financial_analyzer_dataclass import CompanyFinancialData


warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

@dataclass
class RankingCriteria:
    """Critérios para classificação personalizada."""
    eva_weight: float = 0.3
    efv_weight: float = 0.3
    upside_weight: float = 0.2
    profitability_weight: float = 0.1
    liquidity_weight: float = 0.1
    
    def normalize_weights(self):
        """Normaliza os pesos para somar 1.0."""
        total = (self.eva_weight + self.efv_weight + self.upside_weight + 
                 self.profitability_weight + self.liquidity_weight)
        if total > 0:
            self.eva_weight /= total
            self.efv_weight /= total
            self.upside_weight /= total
            self.profitability_weight /= total
            self.liquidity_weight /= total
        else:
            logger.warning("Soma dos pesos é zero, não foi possível normalizar.")

class AdvancedRanking:
    """Classe para classificações e análises avançadas."""
    
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator
        self.scaler = StandardScaler()
        self.min_max_scaler = MinMaxScaler()
        
    def _prepare_data_for_ml(self, companies_data: Dict[str, CompanyFinancialData]) -> pd.DataFrame:
        """Prepara os dados para algoritmos de ML, calculando métricas e tratando NaNs."""
        data_for_ml = []
        for ticker, data in companies_data.items():
            beta = 1.0 
            
            eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            riqueza_atual = self.calculator.calculate_riqueza_atual(data, beta)
            riqueza_futura = self.calculator.calculate_riqueza_futura(data)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan

            data_for_ml.append({
                'ticker': ticker,
                'company_name': data.company_name,
                'eva_pct': eva_pct, 'efv_pct': efv_pct,
                'upside_pct': upside, 'riqueza_atual': riqueza_atual,
                'riqueza_futura': riqueza_futura, 'market_cap': data.market_cap,
                'revenue': data.revenue, 'sector': data.sector
            })
        
        df = pd.DataFrame(data_for_ml)
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
        return df

    def custom_rank_companies(self, companies_data: Dict[str, CompanyFinancialData], criteria: RankingCriteria) -> List[Dict]:
        """Realiza um ranking personalizado de empresas baseado em critérios ponderados."""
        criteria.normalize_weights()
        
        processed_data = []
        # Para escalar, precisamos de todos os dados primeiro
        all_metrics = []
        for ticker, data in companies_data.items():
            beta = 1.0
            eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan
            profitability_score = (data.net_income / data.revenue) * 100 if data.revenue and data.revenue > 0 else 0
            liquidity_score = (data.current_assets / data.current_liabilities) if data.current_liabilities and data.current_liabilities > 0 else 0
            all_metrics.append([eva_pct, efv_pct, upside, profitability_score, liquidity_score])

        metrics_df = pd.DataFrame(all_metrics, columns=['eva_pct', 'efv_pct', 'upside_pct', 'profitability_score', 'liquidity_score'])
        metrics_df = metrics_df.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # Escala todas as métricas de uma vez
        scaled_metrics = self.min_max_scaler.fit_transform(metrics_df)
        
        for i, (ticker, data) in enumerate(companies_data.items()):
            scaled_eva, scaled_efv, scaled_upside, scaled_profitability, scaled_liquidity = scaled_metrics[i]
            
            final_score = (scaled_eva * criteria.eva_weight +
                           scaled_efv * criteria.efv_weight +
                           scaled_upside * criteria.upside_weight +
                           scaled_profitability * criteria.profitability_weight +
                           scaled_liquidity * criteria.liquidity_weight)
            
            processed_data.append({
                'ticker': ticker, 'company_name': data.company_name,
                'eva_pct': metrics_df.iloc[i]['eva_pct'], 'efv_pct': metrics_df.iloc[i]['efv_pct'],
                'upside_pct': metrics_df.iloc[i]['upside_pct'], 'final_score': final_score
            })
        
        processed_data.sort(key=lambda x: x['final_score'], reverse=True)
        return processed_data

    def identify_opportunities(self, companies_data: Dict[str, CompanyFinancialData]) -> Dict[str, Any]:
        """Identifica oportunidades de investimento com base nas métricas de valor."""
        opportunities = {
            'value_creators': [], 'growth_potential': [],
            'undervalued': [], 'best_opportunities': [],
            'clusters': {}, 'sector_rankings': {}
        }
        all_metrics_df = self._prepare_data_for_ml(companies_data)
        if all_metrics_df.empty:
            return opportunities

        for _, row in all_metrics_df.iterrows():
            if row['eva_pct'] > 0:
                opportunities['value_creators'].append((row['ticker'], row['eva_pct']))
            if row['efv_pct'] > 0:
                opportunities['growth_potential'].append((row['ticker'], row['efv_pct']))
            if row['upside_pct'] > 20:
                opportunities['undervalued'].append((row['ticker'], row['upside_pct']))

        all_metrics_df['simple_combined_score'] = (all_metrics_df['eva_pct'] * 0.4 + all_metrics_df['efv_pct'] * 0.4 + all_metrics_df['upside_pct'] * 0.2)
        top_companies = all_metrics_df.sort_values(by='simple_combined_score', ascending=False).head(5)
        for _, row in top_companies.iterrows():
            reason = [r for r, c in [('EVA Positivo', 'eva_pct'), ('EFV Positivo', 'efv_pct'), ('Upside', 'upside_pct')] if row[c] > 0]
            opportunities['best_opportunities'].append((row['ticker'], ", ".join(reason), row['simple_combined_score']))

        features = all_metrics_df[['eva_pct', 'efv_pct', 'upside_pct', 'riqueza_atual', 'riqueza_futura']]
        scaled_features = self.scaler.fit_transform(features)
        
        try:
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            all_metrics_df['cluster'] = kmeans.fit_predict(scaled_features)
            for cluster_id in sorted(all_metrics_df['cluster'].unique()):
                cluster_companies = all_metrics_df[all_metrics_df['cluster'] == cluster_id]['ticker'].tolist()
                opportunities['clusters'][f"Cluster {cluster_id + 1}"] = cluster_companies
        except Exception as e:
            logger.warning(f"Erro no clustering K-Means: {e}.")
        
        return opportunities

class PortfolioOptimizer:
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def suggest_portfolio_allocation(self, companies_data: Dict[str, CompanyFinancialData], profile: str = 'moderate') -> Dict[str, float]:
        """Sugere uma alocação de portfólio baseada em um score de valor."""
        processed_data = []
        for ticker, data in companies_data.items():
            beta = 1.0
            _, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan
            score = np.nan_to_num(eva_pct) + np.nan_to_num(efv_pct) * 1.5 + np.nan_to_num(upside)
            processed_data.append({'ticker': ticker, 'score': score})
        
        df = pd.DataFrame(processed_data).replace([np.inf, -np.inf], np.nan).fillna(0)
        df_positive = df[df['score'] > 0].sort_values(by='score', ascending=False)
        
        if df_positive.empty:
            return {row['ticker']: 0.0 for _, row in df.iterrows()}
        
        total_positive_score = df_positive['score'].sum()
        if total_positive_score <= 0:
            return {row['ticker']: 1/len(df_positive) for _, row in df_positive.iterrows()}
        
        portfolio_weights = {row['ticker']: row['score'] / total_positive_score for _, row in df_positive.iterrows()}
        return {k: round(v, 4) for k, v in portfolio_weights.items()}

    def calculate_portfolio_eva(self, portfolio_weights: Dict[str, float], companies_data: Dict[str, CompanyFinancialData]) -> Tuple[float, float]:
        total_portfolio_eva_abs = 0.0
        total_portfolio_capital_employed = 0.0
        for ticker, weight in portfolio_weights.items():
            if ticker in companies_data:
                company_data = companies_data[ticker]
                beta = 1.0
                eva_abs, _ = self.calculator.calculate_eva(company_data, beta)
                capital_employed = self.calculator._calculate_capital_employed(company_data)
                if not np.isnan(eva_abs) and not np.isnan(capital_employed):
                    total_portfolio_eva_abs += eva_abs * weight
                    total_portfolio_capital_employed += capital_employed * weight
        
        portfolio_eva_pct = (total_portfolio_eva_abs / total_portfolio_capital_employed) * 100 if total_portfolio_capital_employed > 0 else np.nan
        return total_portfolio_eva_abs, portfolio_eva_pct
