# backend/src/advanced_ranking.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import logging
from financial_analyzer import FinancialMetricsCalculator, CompanyFinancialData
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

@dataclass
class RankingCriteria:
    """Critérios para classificação personalizada.
    Permite ajustar os pesos para diferentes métricas de valor.
    """
    eva_weight: float = 0.3
    efv_weight: float = 0.3
    upside_weight: float = 0.2
    profitability_weight: float = 0.1 # Placeholder, a ser calculado
    liquidity_weight: float = 0.1     # Placeholder, a ser calculado
    
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
    """Classe para classificações avançadas e análises sofisticadas,
    baseadas nas análises de correlação e value drivers do TCC.
    """
    
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator
        self.scaler = StandardScaler()
        self.min_max_scaler = MinMaxScaler()
        
    def _prepare_data_for_ml(self, companies_data: Dict[str, CompanyFinancialData]) -> pd.DataFrame:
        """
        Prepara os dados para algoritmos de ML, calculando métricas e lidando com NaNs.
        Foca em métricas que o TCC correlaciona (EVA%, EFV%, Upside%, Riqueza).
        """
        data_for_ml = []
        for ticker, data in companies_data.items():
            # Beta hardcoded para demo. Em produção, seria calculado ou estimado.
            beta = 1.0 
            
            # Recalcular métricas para garantir valores consistentes
            eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            riqueza_atual = self.calculator.calculate_riqueza_atual(data, beta)
            riqueza_futura = self.calculator.calculate_riqueza_futura(data)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan

            # Adicionar métricas adicionais que podem ser úteis para clustering/ranking
            # Ex: ROE, Liquidez Corrente, etc.
            # No TCC, há menção a "margem operacional", "giro dos estoques", "custo de capital próprio/terceiros"
            # Precisaríamos adicionar esses ao CompanyFinancialData ou calculá-los aqui se fossem para ML.
            
            # Para o clustering/ranking avançado, focaremos nas métricas de valor já calculadas
            data_for_ml.append({
                'ticker': ticker,
                'company_name': data.company_name,
                'eva_pct': eva_pct,
                'efv_pct': efv_pct,
                'upside_pct': upside,
                'riqueza_atual': riqueza_atual,
                'riqueza_futura': riqueza_futura,
                'market_cap': data.market_cap, # Pode ser usado como feature ou para ponderação
                'revenue': data.revenue # Pode ser usado como feature ou para ponderação
            })
        
        df = pd.DataFrame(data_for_ml)
        
        # Limpar NaNs/Infinitos para o ML, substituindo por 0 ou média/mediana
        df = df.replace([np.inf, -np.inf], np.nan)
        # Preencher NaNs com 0 para não quebrar o scaler/kmeans. 
        # Em um sistema real, seria melhor imputar com a média/mediana do grupo ou usar um algoritmo que lide com NaNs.
        df = df.fillna(0) 
        
        return df

    def custom_rank_companies(self, companies_data: Dict[str, CompanyFinancialData], criteria: RankingCriteria) -> List[Dict]:
        """
        Realiza um ranking personalizado de empresas baseado em critérios ponderados.
        Baseado na ideia de "critérios customizáveis com pesos ajustáveis" do Plano de Melhorias.
        """
        criteria.normalize_weights()
        
        processed_data = []
        for ticker, data in companies_data.items():
            # Beta hardcoded para demo
            beta = 1.0

            eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan
            
            # Placeholder para scores de rentabilidade e liquidez, que seriam calculados
            profitability_score = (data.net_income / data.revenue) * 100 if data.revenue > 0 else 0
            liquidity_score = (data.current_assets / data.current_liabilities) * 100 if data.current_liabilities > 0 else 0

            # Normalizar métricas para ponderação (MinMaxScaler é robusto para valores com diferentes magnitudes)
            # É importante escalar as métricas para que os pesos funcionem corretamente.
            scaled_eva = self.min_max_scaler.fit_transform(np.array([[eva_pct]])) if not np.isnan(eva_pct) else 0
            scaled_efv = self.min_max_scaler.fit_transform(np.array([[efv_pct]])) if not np.isnan(efv_pct) else 0
            scaled_upside = self.min_max_scaler.fit_transform(np.array([[upside]])) if not np.isnan(upside) else 0
            scaled_profitability = self.min_max_scaler.fit_transform(np.array([[profitability_score]])) if not np.isnan(profitability_score) else 0
            scaled_liquidity = self.min_max_scaler.fit_transform(np.array([[liquidity_score]])) if not np.isnan(liquidity_score) else 0

            final_score = (scaled_eva * criteria.eva_weight +
                           scaled_efv * criteria.efv_weight +
                           scaled_upside * criteria.upside_weight +
                           scaled_profitability * criteria.profitability_weight +
                           scaled_liquidity * criteria.liquidity_weight)
            
            processed_data.append({
                'ticker': ticker,
                'company_name': data.company_name,
                'eva_pct': eva_pct,
                'efv_pct': efv_pct,
                'upside_pct': upside,
                'profitability_score': profitability_score,
                'liquidity_score': liquidity_score,
                'final_score': final_score[0][0] if isinstance(final_score, np.ndarray) else final_score
            })
        
        # Ordenar pelo score final
        processed_data.sort(key=lambda x: x['final_score'], reverse=True)
        return processed_data

    def identify_opportunities(self, companies_data: Dict[str, CompanyFinancialData]) -> Dict[str, Any]:
        """
        Identifica oportunidades de investimento com base nas métricas de valor.
        Baseado nos insights automáticos do Plano de Melhorias.
        """
        opportunities = {
            'value_creators': [],       # EVA > 0
            'growth_potential': [],     # EFV > 0
            'undervalued': [],          # Upside > 20% (exemplo de critério)
            'best_opportunities': [],   # Combinação de critérios
            'clusters': {},             # Agrupamento de empresas (se K-Means for usado)
            'sector_rankings': {}       # Ranking por setor (se setores forem identificados)
        }

        # Primeiro, calcular métricas para todas as empresas
        all_metrics_df = self._prepare_data_for_ml(companies_data)
        
        if all_metrics_df.empty:
            return opportunities

        # Análise de Value Creators e Growth Potential
        for _, row in all_metrics_df.iterrows():
            if row['eva_pct'] > 0:
                opportunities['value_creators'].append((row['ticker'], row['eva_pct']))
            if row['efv_pct'] > 0:
                opportunities['growth_potential'].append((row['ticker'], row['efv_pct']))
            if row['upside_pct'] > 20: # Exemplo de threshold para subvalorizadas
                opportunities['undervalued'].append((row['ticker'], row['upside_pct']))

        # Classificar e pegar as melhores oportunidades
        # Usar o 'final_score' se o custom_rank_companies foi rodado, ou criar um aqui
        # Para simplificar na demo, vamos criar um score simples aqui
        all_metrics_df['simple_combined_score'] = (all_metrics_df['eva_pct'] * 0.4 + 
                                                   all_metrics_df['efv_pct'] * 0.4 + 
                                                   all_metrics_df['upside_pct'] * 0.2)
        
        top_companies = all_metrics_df.sort_values(by='simple_combined_score', ascending=False).head(5)
        for _, row in top_companies.iterrows():
            reason = []
            if row['eva_pct'] > 0: reason.append('EVA Positivo')
            if row['efv_pct'] > 0: reason.append('EFV Positivo')
            if row['upside_pct'] > 0: reason.append('Upside')
            opportunities['best_opportunities'].append((row['ticker'], ", ".join(reason), row['simple_combined_score']))

        # Agrupamento (Clustering) - K-Means
        # Selecionar features numéricas para clustering
        features = all_metrics_df[['eva_pct', 'efv_pct', 'upside_pct', 'riqueza_atual', 'riqueza_futura']]
        # Escalonar os dados antes do clustering
        scaled_features = self.scaler.fit_transform(features)
        
        # Reduzir dimensionalidade com PCA se muitas features (opcional, para mais features)
        # pca = PCA(n_components=2)
        # reduced_features = pca.fit_transform(scaled_features)

        # Aplicar K-Means (exemplo com 3 clusters)
        try:
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10) # n_init para evitar warning
            clusters = kmeans.fit_predict(scaled_features)
            all_metrics_df['cluster'] = clusters

            for cluster_id in sorted(all_metrics_df['cluster'].unique()):
                cluster_companies = all_metrics_df[all_metrics_df['cluster'] == cluster_id]['ticker'].tolist()
                opportunities['clusters'][f"Cluster {cluster_id + 1}"] = cluster_companies
        except Exception as e:
            logger.warning(f"Erro ao realizar clustering K-Means: {e}. Ignorando clustering nesta execução.")
            opportunities['clusters']['Erro no Clustering'] = ["Não foi possível agrupar as empresas."]

        # Ranking por Setor (requer que 'sector' esteja nos dados, ou usar ibovespa_data.get_market_sectors)
        # Para este demo, vamos usar a função get_market_sectors de ibovespa_data para simular
        from ibovespa_data import get_market_sectors
        sectors_map = get_market_sectors()
        # Inverter o mapa para ter ticker -> setor
        ticker_to_sector = {}
        for sector, tickers in sectors_map.items():
            for ticker in tickers:
                ticker_to_sector[ticker] = sector
        
        all_metrics_df['sector'] = all_metrics_df['ticker'].map(ticker_to_sector)
        
        for sector_name in all_metrics_df['sector'].dropna().unique():
            sector_df = all_metrics_df[all_metrics_df['sector'] == sector_name]
            if not sector_df.empty:
                sector_ranking = sector_df.sort_values(by='simple_combined_score', ascending=False)[['ticker', 'simple_combined_score']].values.tolist()
                opportunities['sector_rankings'][sector_name] = sector_ranking
                
        return opportunities

class PortfolioOptimizer:
    """
    Classe para sugestão e otimização de portfólio.
    Baseado na otimização de portfólio e perfis de risco do Plano de Melhorias.
    """
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def suggest_portfolio_allocation(self, companies_data: Dict[str, CompanyFinancialData], profile: str = 'moderate') -> Dict[str, float]:
        """
        Sugere uma alocação de portfólio baseada nas métricas de valor e perfil de risco.
        Esta é uma simplificação para demonstração. Otimização real requer otimizadores complexos.
        """
        processed_data = []
        for ticker, data in companies_data.items():
            beta = 1.0 # Exemplo
            eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan
            
            # Criar um score interno para ponderar a alocação
            score = 0
            if not np.isnan(eva_pct): score += eva_pct
            if not np.isnan(efv_pct): score += efv_pct * 1.5 # Maior peso para potencial futuro
            if not np.isnan(upside): score += upside
            
            processed_data.append({'ticker': ticker, 'score': score})
        
        df = pd.DataFrame(processed_data).replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # Ordenar por score e alocar pesos
        df = df.sort_values(by='score', ascending=False)
        
        total_score = df['score'].sum()
        if total_score == 0:
            return {c.ticker: 0.0 for c in companies_data.values()} # Retorna 0% para todos se não houver score

        portfolio_weights = {}
        if profile == 'conservative':
            # Mais peso para as top 5, mas ainda diversificado
            top_n = min(len(df), 5) 
            total_top_score = df['score'].head(top_n).sum()
            if total_top_score > 0:
                for _, row in df.head(top_n).iterrows():
                    portfolio_weights[row['ticker']] = (row['score'] / total_top_score) * 0.7 # 70% nas top N
                remaining_tickers = df.iloc[top_n:]
                remaining_total_score = remaining_tickers['score'].sum()
                if remaining_total_score > 0:
                    for _, row in remaining_tickers.iterrows():
                        portfolio_weights[row['ticker']] = (row['score'] / remaining_total_score) * 0.3 # 30% nas restantes
            else:
                # Se top scores forem 0, distribuir igualmente
                for _, row in df.iterrows():
                    portfolio_weights[row['ticker']] = 1 / len(df) if len(df) > 0 else 0
        elif profile == 'aggressive':
            # Concentra mais nas top 3
            top_n = min(len(df), 3)
            total_top_score = df['score'].head(top_n).sum()
            if total_top_score > 0:
                for _, row in df.head(top_n).iterrows():
                    portfolio_weights[row['ticker']] = (row['score'] / total_top_score) * 0.8 # 80% nas top N
                remaining_tickers = df.iloc[top_n:]
                remaining_total_score = remaining_tickers['score'].sum()
                if remaining_total_score > 0:
                    for _, row in remaining_tickers.iterrows():
                        portfolio_weights[row['ticker']] = (row['score'] / remaining_total_score) * 0.2 # 20% nas restantes
            else:
                 # Se top scores forem 0, distribuir igualmente
                for _, row in df.iterrows():
                    portfolio_weights[row['ticker']] = 1 / len(df) if len(df) > 0 else 0
        else: # Moderate (default)
            # Distribuição mais linear, mas ainda favorecendo os melhores
            for _, row in df.iterrows():
                portfolio_weights[row['ticker']] = row['score'] / total_score
        
        # Ajustar para que a soma seja 1.0 (ou 100%)
        current_sum = sum(portfolio_weights.values())
        if current_sum > 0:
            for ticker in portfolio_weights:
                portfolio_weights[ticker] /= current_sum
        
        return {k: round(v, 4) for k, v in portfolio_weights.items()} # Arredondar para 4 casas decimais

    def calculate_portfolio_eva(self, portfolio_weights: Dict[str, float], companies_data: Dict[str, CompanyFinancialData]) -> Tuple[float, float]:
        """
        Calcula o EVA (absoluto e percentual) de um portfólio.
        """
        total_portfolio_eva_abs = 0.0
        total_portfolio_capital_employed = 0.0

        for ticker, weight in portfolio_weights.items():
            if ticker in companies_data:
                company_data = companies_data[ticker]
                beta = 1.0 # Exemplo
                eva_abs, _ = self.calculator.calculate_eva(company_data, beta)
                capital_employed = self.calculator._calculate_capital_employed(company_data)
                
                if not np.isnan(eva_abs) and not np.isnan(capital_employed):
                    # Ponderar EVA pelo peso no portfólio (ou pelo capital empregado da empresa ponderado pelo peso no portfólio)
                    # Para EVA agregado do portfólio, é mais comum somar os EVAs ponderados
                    total_portfolio_eva_abs += eva_abs * weight
                    total_portfolio_capital_employed += capital_employed * weight # Isso não é exato, precisaria do capital total do portfólio
        
        # Para um EVA percentual do portfólio, é mais robusto calcular o WACC e ROCE médios do portfólio
        # e aplicar à soma do capital empregado do portfólio.
        # Aqui, uma simplificação: EVA abs / capital empregado médio ponderado
        if total_portfolio_capital_employed > 0:
            portfolio_eva_pct = (total_portfolio_eva_abs / total_portfolio_capital_employed) * 100
        else:
            portfolio_eva_pct = np.nan # Não pode calcular se o capital total é zero

        return total_portfolio_eva_abs, portfolio_eva_pct

if __name__ == '__main__':
    from ibovespa_data import get_ibovespa_tickers, get_selic_rate
    from utils import format_currency, format_percentage, PerformanceMonitor
    from financial_analyzer import FinancialDataCollector, FinancialMetricsCalculator

    monitor = PerformanceMonitor()
    monitor.start_timer("advanced_ranking_and_portfolio_demo")

    # 1. Coleta de dados
    collector = FinancialDataCollector()
    tickers_to_analyze = get_ibovespa_tickers()[:10] # Reduzir para demo mais rápida
    
    print(f"Coletando dados para {len(tickers_to_analyze)} empresas para análise avançada: {', '.join(tickers_to_analyze)}...")
    companies_data = collector.get_multiple_companies(tickers_to_analyze)

    if not companies_data:
        print("Nenhuma empresa coletada. Abortando demo de ranking avançado.")
    else:
        # 2. Inicializar calculadora e sistemas avançados
        selic_rate = get_selic_rate()
        calculator = FinancialMetricsCalculator(selic_rate=selic_rate)
        advanced_ranking = AdvancedRanking(calculator)
        portfolio_optimizer = PortfolioOptimizer(calculator)

        # 3. Ranking Personalizado
        print("\n=== RANKING PERSONALIZADO ===")
        custom_criteria = RankingCriteria(eva_weight=0.4, efv_weight=0.3, upside_weight=0.2, profitability_weight=0.05, liquidity_weight=0.05)
        custom_ranking = advanced_ranking.custom_rank_companies(companies_data, custom_criteria)
        print("Top 5 do Ranking Personalizado:")
        for i, company in enumerate(custom_ranking[:5], 1):
            print(f"{i}. {company['ticker']} - Score: {company['final_score']:.2f} (EVA: {format_percentage(company['eva_pct'])}, EFV: {format_percentage(company['efv_pct'])})")

        # 4. Identificação de Oportunidades
        print("\n=== IDENTIFICAÇÃO DE OPORTUNIDADES ===")
        opportunities = advanced_ranking.identify_opportunities(companies_data)
        
        print("\nEmpresas Criadoras de Valor (EVA Positivo):")
        for ticker, eva_pct in opportunities['value_creators']:
            print(f"  {ticker}: EVA = {format_percentage(eva_pct)}")
        
        print("\nEmpresas com Potencial de Crescimento (EFV Positivo):")
        for ticker, efv_pct in opportunities['growth_potential']:
            print(f"  {ticker}: EFV = {format_percentage(efv_pct)}")
        
        print("\nAções Subvalorizadas (Upside > 20%):")
        for ticker, upside in opportunities['undervalued']:
            print(f"  {ticker}: Upside = {format_percentage(upside)}")
        
        print("\nMelhores Oportunidades (Score Combinado):")
        for ticker, reason, score in opportunities['best_opportunities']:
            print(f"  {ticker}: {reason} (Score: {score:.1f})")
        
        print("\nClusters de Empresas:")
        for cluster_name, companies in opportunities['clusters'].items():
            print(f"  {cluster_name}: {', '.join(companies)}")
        
        print("\nRankings por Setor:")
        for sector, rankings in opportunities['sector_rankings'].items():
            print(f"  {sector}:")
            for i, (ticker, score) in enumerate(rankings, 1):
                print(f"    {i}. {ticker}: {score:.1f}")
        
        # 5. Sugestão de Portfólio
        print("\n=== SUGESTÃO DE PORTFÓLIO (Moderado) ===")
        portfolio_weights = portfolio_optimizer.suggest_portfolio_allocation(companies_data, 'moderate')
        for ticker, weight in portfolio_weights.items():
            print(f"  {ticker}: {weight*100:.1f}%")
        
        # 6. EVA do Portfólio
        portfolio_eva_abs, portfolio_eva_pct = portfolio_optimizer.calculate_portfolio_eva(portfolio_weights, companies_data)
        if not np.isnan(portfolio_eva_pct):
            print(f"\nEVA do Portfólio Sugerido: {format_percentage(portfolio_eva_pct)} ({format_currency(portfolio_eva_abs)})")
        else:
            print("\nNão foi possível calcular o EVA do portfólio.")

    monitor.end_timer("advanced_ranking_and_portfolio_demo")
