# backend/src/advanced_ranking.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import KMeans

# Import das classes de cálculo de métricas
from financial_analyzer import FinancialMetricsCalculator
from financial_analyzer_dataclass import CompanyFinancialData

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')

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
        """Prepara dados para ML: calcula métricas e trata NaNs."""
        records = []
        for ticker, data in companies_data.items():
            try:
                beta = 1.0
                eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
                efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
                riqueza_atual = self.calculator.calculate_riqueza_atual(data, beta)
                riqueza_futura = self.calculator.calculate_riqueza_futura(data)
                upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(eva_abs) else np.nan
                # Profitability and liquidity if available
                rev = getattr(data, 'revenue', None)
                net_inc = getattr(data, 'net_income', None)
                profitability = (net_inc / rev * 100) if rev and rev > 0 and net_inc is not None else np.nan
                curr_assets = getattr(data, 'current_assets', None)
                curr_liab = getattr(data, 'current_liabilities', None)
                liquidity = (curr_assets / curr_liab) if curr_assets is not None and curr_liab and curr_liab > 0 else np.nan
                records.append({
                    'ticker': ticker,
                    'company_name': data.company_name,
                    'eva_pct': eva_pct,
                    'efv_pct': efv_pct,
                    'upside_pct': upside,
                    'riqueza_atual': riqueza_atual,
                    'riqueza_futura': riqueza_futura,
                    'market_cap': getattr(data, 'market_cap', np.nan),
                    'profitability': profitability,
                    'liquidity': liquidity,
                    'sector': getattr(data, 'sector', None)
                })
            except Exception as e:
                logger.error(f"Erro ao preparar dados para {ticker}: {e}")
        df = pd.DataFrame(records)
        # Substitui inf e nulls
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        # Preenche NaN com zeros ou mediana dependendo da coluna
        numeric_cols = ['eva_pct', 'efv_pct', 'upside_pct', 'riqueza_atual', 'riqueza_futura', 'market_cap', 'profitability', 'liquidity']
        for col in numeric_cols:
            if col in df.columns:
                median = df[col].median(skipna=True)
                df[col].fillna(median if not np.isnan(median) else 0, inplace=True)
        return df

    def custom_rank_companies(self, companies_data: Dict[str, CompanyFinancialData], criteria: RankingCriteria) -> List[Dict]:
        """Ranking personalizado baseado em critérios ponderados."""
        criteria.normalize_weights()
        df = self._prepare_data_for_ml(companies_data)
        if df.empty:
            return []
        # Seleciona colunas de métricas
        metrics = df[['eva_pct', 'efv_pct', 'upside_pct', 'profitability', 'liquidity']].values
        # Escala entre 0 e 1
        scaled = self.min_max_scaler.fit_transform(metrics)
        results = []
        for idx, row in df.iterrows():
            scaled_vals = scaled[idx]
            score = (
                scaled_vals[0] * criteria.eva_weight +
                scaled_vals[1] * criteria.efv_weight +
                scaled_vals[2] * criteria.upside_weight +
                scaled_vals[3] * criteria.profitability_weight +
                scaled_vals[4] * criteria.liquidity_weight
            )
            results.append({
                'ticker': row['ticker'],
                'company_name': row['company_name'],
                'eva_pct': row['eva_pct'],
                'efv_pct': row['efv_pct'],
                'upside_pct': row['upside_pct'],
                'final_score': score
            })
        # Ordena desc
        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results

    def identify_opportunities(self, companies_data: Dict[str, CompanyFinancialData]) -> Dict[str, Any]:
        """Identifica oportunidades baseado em métricas de valor."""
        opportunities = {
            'value_creators': [], 'growth_potential': [], 'undervalued': [],
            'best_opportunities': [], 'clusters': {}, 'sector_rankings': {}
        }
        df = self._prepare_data_for_ml(companies_data)
        if df.empty:
            return opportunities
        # Value creators e growth
        for _, row in df.iterrows():
            if row['eva_pct'] > 0:
                opportunities['value_creators'].append((row['ticker'], row['eva_pct']))
            if row['efv_pct'] > 0:
                opportunities['growth_potential'].append((row['ticker'], row['efv_pct']))
            if row['upside_pct'] > 20:
                opportunities['undervalued'].append((row['ticker'], row['upside_pct']))
        # Best opportunities: combinado simples
        df['simple_score'] = df['eva_pct'] * 0.4 + df['efv_pct'] * 0.4 + df['upside_pct'] * 0.2
        top5 = df.nlargest(5, 'simple_score')
        for _, row in top5.iterrows():
            reasons = []
            if row['eva_pct'] > 0: reasons.append('EVA Positivo')
            if row['efv_pct'] > 0: reasons.append('EFV Positivo')
            if row['upside_pct'] > 0: reasons.append('Upside')
            opportunities['best_opportunities'].append((row['ticker'], ", ".join(reasons), row['simple_score']))
        # Clustering KMeans
        features = df[['eva_pct', 'efv_pct', 'upside_pct', 'riqueza_atual', 'riqueza_futura']]
        features.replace([np.inf, -np.inf], np.nan, inplace=True)
        features.fillna(features.median(), inplace=True)
        try:
            scaled = self.scaler.fit_transform(features)
            n_clusters = min(3, len(df))
            if n_clusters >= 1:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                labels = kmeans.fit_predict(scaled)
                df['cluster'] = labels
n            for cid in sorted(df['cluster'].unique()):
                cluster_list = df[df['cluster'] == cid]['ticker'].tolist()
                opportunities['clusters'][f"Cluster {cid+1}"] = cluster_list
        except Exception as e:
            logger.warning(f"Erro no clustering K-Means: {e}")
        # Sector rankings: agrupa por setor se disponível
        if 'sector' in df.columns:
            try:
                sector_groups = df.groupby('sector')
                for sector, group in sector_groups:
                    # classificar por simple_score
                    top = group.nlargest(3, 'simple_score')['ticker'].tolist()
                    opportunities['sector_rankings'][sector] = top
            except Exception as e:
                logger.warning(f"Erro em sector_rankings: {e}")
        return opportunities

class PortfolioOptimizer:
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def suggest_portfolio_allocation(self, companies_data: Dict[str, CompanyFinancialData], profile: str = 'moderate') -> Dict[str, float]:
        """Sugere alocação de portfólio baseada em score de valor."""
        scored = []
        for ticker, data in companies_data.items():
            try:
                beta = 1.0
                _, eva_pct = self.calculator.calculate_eva(data, beta)
                efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
                upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(eva_pct) else np.nan
                score = np.nan_to_num(eva_pct) + np.nan_to_num(efv_pct) * 1.5 + np.nan_to_num(upside)
                scored.append({'ticker': ticker, 'score': score})
            except Exception as e:
                logger.error(f"Erro ao calcular score para {ticker}: {e}")
        df = pd.DataFrame(scored)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)
        df_positive = df[df['score'] > 0]
        if df_positive.empty:
            return {row['ticker']: 0.0 for _, row in df.iterrows()}
        total = df_positive['score'].sum()
        if total <= 0:
            count = len(df_positive)
            return {row['ticker']: round(1/count, 4) for _, row in df_positive.iterrows()}
        weights = {row['ticker']: round(row['score']/total, 4) for _, row in df_positive.iterrows()}
        return weights

    def calculate_portfolio_eva(self, portfolio_weights: Dict[str, float], companies_data: Dict[str, CompanyFinancialData]) -> Tuple[float, float]:
        total_eva = 0.0
        total_capital = 0.0
        for ticker, weight in portfolio_weights.items():
            data = companies_data.get(ticker)
            if not data:
                continue
            try:
                beta = 1.0
                eva_abs, _ = self.calculator.calculate_eva(data, beta)
                cap_emp = self.calculator._calculate_capital_employed(data)
                if not np.isnan(eva_abs) and not np.isnan(cap_emp):
                    total_eva += eva_abs * weight
                    total_capital += cap_emp * weight
            except Exception as e:
                logger.error(f"Erro no cálculo de EVA de portfólio para {ticker}: {e}")
        portfolio_eva_pct = (total_eva / total_capital) * 100 if total_capital > 0 else np.nan
        return total_eva, portfolio_eva_pct
