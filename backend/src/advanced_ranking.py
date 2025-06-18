# backend/src/advanced_ranking.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Import das classes de cálculo de métricas e de dados
from financial_analyzer import FinancialMetricsCalculator
from financial_analyzer_dataclass import CompanyFinancialData

# Configuração do logger
logger = logging.getLogger(__name__)


@dataclass
class RankingCriteria:
    """Critérios para classificação personalizada."""
    eva_weight: float = 0.4
    efv_weight: float = 0.3
    upside_weight: float = 0.3

    def normalize_weights(self):
        """Normaliza os pesos para somar 1.0."""
        total = self.eva_weight + self.efv_weight + self.upside_weight
        if total > 0:
            self.eva_weight /= total
            self.efv_weight /= total
            self.upside_weight /= total
        else:
            logger.warning("Soma dos pesos é zero, não foi possível normalizar.")


class AdvancedRanking:
    """Classe para classificações e análises avançadas usando clustering."""

    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def create_clusters(self, companies_data: List[CompanyFinancialData], n_clusters: int = 4) -> pd.DataFrame:
        """
        Agrupa empresas em clusters com base em suas métricas financeiras.
        Retorna um DataFrame com as empresas e seus clusters atribuídos.
        """
        metrics_list = []
        for data in companies_data:
            try:
                beta = 1.0  # Beta padrão para simplificação
                _, eva_pct = self.calculator.calculate_eva(data, beta)
                _, efv_pct = self.calculator.calculate_efv(data, beta)
                upside = self.calculator.calculate_upside(data, beta)
                
                # Garante que temos valores numéricos para clustering
                if all(np.isfinite([eva_pct, efv_pct, upside])):
                    metrics_list.append({
                        'ticker': data.ticker,
                        'eva_percentual': eva_pct,
                        'efv_percentual': efv_pct,
                        'upside_percentual': upside
                    })
            except Exception as e:
                logger.error(f"Erro ao calcular métricas para clustering de {data.ticker}: {e}")

        if not metrics_list:
            logger.warning("Nenhuma empresa com métricas válidas para clustering.")
            return pd.DataFrame()

        df = pd.DataFrame(metrics_list)
        features = df[['eva_percentual', 'efv_percentual', 'upside_percentual']]
        
        # Normaliza os dados para que o KMeans funcione corretamente
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        # Aplica o KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(scaled_features)
        
        return df

    def analyze_clusters(self, df_clustered: pd.DataFrame) -> Dict[str, Any]:
        """
        Analisa as características de cada cluster.
        Retorna um dicionário com estatísticas por cluster.
        """
        if df_clustered.empty:
            return {}

        analysis = {}
        for cid in sorted(df_clustered['cluster'].unique()):
            cluster_df = df_clustered[df_clustered['cluster'] == cid]
            analysis[f'cluster_{cid}'] = {
                'count': len(cluster_df),
                'tickers': cluster_df['ticker'].tolist(),
                'mean_eva_pct': cluster_df['eva_percentual'].mean(),
                'mean_efv_pct': cluster_df['efv_percentual'].mean(),
                'mean_upside_pct': cluster_df['upside_percentual'].mean()
            }
        return analysis


class PortfolioOptimizer:
    """
    Otimiza a alocação de um portfólio com base nos resultados da análise.
    """
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def create_score_based_weights(self, ranked_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Cria pesos para o portfólio com base no score combinado.
        Apenas empresas com score positivo são incluídas.
        """
        df = pd.DataFrame([
            {'ticker': item['ticker'], 'score': item['metrics'].get('combined_score', 0)}
            for item in ranked_data
        ])
        
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)
        
        df_positive = df[df['score'] > 0]
        if df_positive.empty:
            return {row['ticker']: 0.0 for _, row in df.iterrows()}
            
        total_score = df_positive['score'].sum()
        if total_score <= 0:
            count = len(df_positive)
            return {row['ticker']: round(1 / count, 4) for _, row in df_positive.iterrows()} if count > 0 else {}
            
        weights = {row['ticker']: round(row['score'] / total_score, 4) for _, row in df_positive.iterrows()}
        return weights

    def calculate_portfolio_eva(self, portfolio_weights: Dict[str, float], companies_data_map: Dict[str, CompanyFinancialData]) -> Tuple[float, float]:
        """
        Calcula o EVA agregado de um portfólio ponderado.
        """
        total_eva = 0.0
        total_capital = 0.0

        for ticker, weight in portfolio_weights.items():
            data = companies_data_map.get(ticker)
            if not data:
                continue
            
            # --- CORREÇÃO APLICADA AQUI ---
            # O bloco 'try' foi completado com um 'except' para ser sintaticamente válido.
            try:
                beta = 1.0 # Beta padrão para simplificação
                eva_abs, _ = self.calculator.calculate_eva(data, beta)
                cap_emp = self.calculator._calculate_capital_employed(data)
                
                if not np.isnan(eva_abs) and not np.isnan(cap_emp):
                    total_eva += eva_abs * weight
                    total_capital += cap_emp * weight
            except Exception as e:
                # Adiciona um log de erro para depuração sem travar a aplicação.
                logger.error(f"Erro no cálculo de EVA de portfólio para {ticker}: {e}")

        if total_capital <= 0:
            return total_eva, 0.0
            
        portfolio_eva_pct = (total_eva / total_capital) * 100
        return total_eva, portfolio_eva_pct
