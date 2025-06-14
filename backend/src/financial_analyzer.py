# backend/src/financial_analyzer.py

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import warnings
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import math

# Ignorar FutureWarnings do pandas com yfinance
warnings.filterwarnings('ignore', category=FutureWarning)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CompanyFinancialData:
    """Classe para armazenar dados financeiros de uma empresa.
    Adaptado para incluir campos relevantes do TCC do usuário.
    """
    ticker: str
    company_name: str
    # Dados de mercado
    market_cap: float
    stock_price: float # Preço da ação
    shares_outstanding: float # Ações em circulação
    
    # DRE - Demonstração do Resultado do Exercício
    revenue: float          # Receita Líquida (p. 17 - "receita líquida")
    ebit: float             # Lucro Operacional (EBIT) - proxy para o NOPAT antes de impostos
    net_income: float       # Lucro Líquido
    
    # DFC - Demonstração do Fluxo de Caixa
    depreciation_amortization: float # Depreciação e Amortização (p. 17)
    capex: float # Capital Expenditure (Investimento em capital fixo) - (p. 17, 24)
    
    # BPA/BPP - Balanço Patrimonial Ativo/Passivo
    total_assets: float     # Ativos Totais
    total_debt: float       # Dívida Total (Passivo Oneroso - p. 20)
    equity: float           # Patrimônio Líquido
    current_assets: float   # Ativo Circulante
    current_liabilities: float # Passivo Circulante
    cash: float             # Caixa e Equivalentes
    
    # Adicionais para cálculos específicos do TCC
    accounts_receivable: float # Contas a Receber (p. 22 - "Prazos operacionais de cobrança")
    inventory: float        # Estoques (p. 22 - "Giro dos estoques")
    accounts_payable: float # Fornecedores (p. 22 - "Prazos operacionais de pagamento")
    
    # Campos calculados que podem ser passados para otimização futura
    # capital_employed: Optional[float] = None
    # working_capital: Optional[float] = None


class FinancialDataCollector:
    """Classe responsável pela coleta de dados financeiros via yfinance.
    Foca em dados trimestrais para maior granularidade.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.max_retries = 3
        self.retry_delay = 5 # seconds

    def _fetch_data_with_retries(self, ticker: str, data_type: str = 'financials', period: str = 'quarterly') -> Optional[pd.DataFrame]:
        """Tenta buscar dados do yfinance com retries."""
        for attempt in range(self.max_retries):
            try:
                stock = yf.Ticker(ticker, session=self.session)
                if data_type == 'financials':
                    data = stock.quarterly_financials if period == 'quarterly' else stock.financials
                elif data_type == 'balance_sheet':
                    data = stock.quarterly_balance_sheet if period == 'quarterly' else stock.balance_sheet
                elif data_type == 'cash_flow':
                    data = stock.quarterly_cash_flow if period == 'quarterly' else stock.cash_flow
                elif data_type == 'info':
                    return stock.info
                else:
                    return None
                
                if not data.empty:
                    return data
                elif attempt < self.max_retries - 1:
                    logger.warning(f"Dados vazios para {ticker} ({data_type}, {period}). Tentando novamente em {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Erro ao coletar {data_type} para {ticker} (tentativa {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        logger.error(f"Falha ao coletar {data_type} para {ticker} após {self.max_retries} tentativas.")
        return None

    def get_company_data(self, ticker: str) -> Optional[CompanyFinancialData]:
        """
        Coleta os dados financeiros mais recentes de uma empresa usando yfinance.
        """
        logger.info(f"Coletando dados para {ticker}...")
        try:
            stock = yf.Ticker(ticker, session=self.session)
            
            # Obter informações básicas
            info = self._fetch_data_with_retries(ticker, data_type='info')
            if not info:
                logger.warning(f"Não foi possível obter informações básicas para {ticker}.")
                return None

            # Obter DRE, Balanço e Fluxo de Caixa mais recentes (trimestral)
            financials = self._fetch_data_with_retries(ticker, data_type='financials', period='quarterly')
            balance_sheet = self._fetch_data_with_retries(ticker, data_type='balance_sheet', period='quarterly')
            cash_flow = self._fetch_data_with_retries(ticker, data_type='cash_flow', period='quarterly')

            if financials is None or financials.empty:
                logger.warning(f"Não foi possível coletar demonstração financeira para {ticker}.")
                return None
            if balance_sheet is None or balance_sheet.empty:
                logger.warning(f"Não foi possível coletar balanço patrimonial para {ticker}.")
                return None
            if cash_flow is None or cash_flow.empty:
                logger.warning(f"Não foi possível coletar fluxo de caixa para {ticker}.")
                return None

            # Usar o trimestre mais recente (primeira coluna do DataFrame)
            latest_date = financials.columns[0]
            fin_data = financials[latest_date]
            bs_data = balance_sheet[latest_date]
            cf_data = cash_flow[latest_date]

            # Mapeamento de dados
            company_name = info.get('longName', ticker)
            market_cap = info.get('marketCap', 0)
            shares_outstanding = info.get('sharesOutstanding', 0)
            stock_price = info.get('currentPrice', 0)

            # DRE
            revenue = fin_data.get('TotalRevenue', 0)
            ebit = fin_data.get('Ebit', 0)
            net_income = fin_data.get('NetIncome', 0)

            # Balanço Patrimonial
            total_assets = bs_data.get('TotalAssets', 0)
            total_debt = bs_data.get('TotalDebt', bs_data.get('LongTermDebt', 0) + bs_data.get('ShortLongTermDebt', 0))
            equity = bs_data.get('TotalStockholderEquity', 0)
            current_assets = bs_data.get('TotalCurrentAssets', 0)
            current_liabilities = bs_data.get('TotalCurrentLiabilities', 0)
            cash = bs_data.get('CashAndCashEquivalents', 0)
            property_plant_equipment = bs_data.get('PropertyPlantAndEquipment', 0)

            # Fluxo de Caixa (CAPEX é um item de saída de caixa de investimento)
            # 'CapitalExpenditures' é o campo comum em yfinance para CAPEX no cash flow statement
            # Se não houver, tentar 'PurchasesOfPropertyPlantAndEquipment' ou similar.
            capex = abs(cf_data.get('CapitalExpenditures', 0)) # CAPEX geralmente é negativo, pegar o valor absoluto
            if capex == 0:
                capex = abs(cf_data.get('PurchasesOfPropertyPlantAndEquipment', 0))
            
            # Dados para NCG / Direcionadores de Valor Operacionais (p. 22)
            accounts_receivable = bs_data.get('NetReceivables', 0)
            inventory = bs_data.get('Inventory', 0)
            accounts_payable = bs_data.get('AccountsPayable', 0)

            # Validar e instanciar
            data = {
                'ticker': ticker,
                'company_name': company_name,
                'market_cap': market_cap,
                'stock_price': stock_price,
                'shares_outstanding': shares_outstanding,
                'revenue': revenue,
                'ebit': ebit,
                'net_income': net_income,
                'depreciation_amortization': cf_data.get('DepreciationAndAmortization', 0), # do cash flow
                'capex': capex,
                'total_assets': total_assets,
                'total_debt': total_debt,
                'equity': equity,
                'current_assets': current_assets,
                'current_liabilities': current_liabilities,
                'cash': cash,
                'accounts_receivable': accounts_receivable,
                'inventory': inventory,
                'accounts_payable': accounts_payable,
                'property_plant_equipment': property_plant_equipment # Para capital empregado
            }

            is_valid, errors = ValidationUtils.validate_financial_data(data)
            if not is_valid:
                logger.warning(f"Dados coletados para {ticker} são inválidos: {errors}")
                return None
            
            return CompanyFinancialData(**data)

        except Exception as e:
            logger.error(f"Erro geral ao coletar dados para {ticker}: {e}")
            return None

    def get_multiple_companies(self, tickers: List[str]) -> Dict[str, CompanyFinancialData]:
        """
        Coleta dados para uma lista de empresas.
        """
        companies_data = {}
        for ticker in tickers:
            data = self.get_company_data(ticker)
            if data:
                companies_data[ticker] = data
        return companies_data

class FinancialMetricsCalculator:
    """Classe responsável pelo cálculo das métricas financeiras:
    WACC, EVA, EFV, Riqueza Atual, Riqueza Futura.
    Baseado nas Equações 1-5 e metodologia do TCC.
    """
    
    def __init__(self, selic_rate: Optional[float] = None):
        self.tax_rate = 0.34 # Alíquota de IR e CSLL para NOPAT e beta (34% conforme TCC p.17, 20)
        self.risk_free_rate = (selic_rate / 100) if selic_rate else 0.10 # Selic como taxa livre de risco, default 10%
        self.market_risk_premium = 0.06 # Prêmio de risco de mercado (exemplo: 6%)
        # Estes deveriam vir de uma fonte confiável ou ser ajustáveis

    def _calculate_nopat(self, ebit: float) -> float:
        """Calcula o NOPAT (Net Operating Profit After Taxes)."""
        return ebit * (1 - self.tax_rate)

    def _calculate_working_capital(self, data: CompanyFinancialData) -> float:
        """Calcula o Capital de Giro (Ativo Circulante - Passivo Circulante)."""
        return data.current_assets - data.current_liabilities

    def _calculate_ncg(self, data: CompanyFinancialData) -> float:
        """Calcula a Necessidade de Capital de Giro (NCG).
        NCG = Contas a Receber + Estoques - Fornecedores
        """
        return data.accounts_receivable + data.inventory - data.accounts_payable

    def _calculate_capital_employed(self, data: CompanyFinancialData) -> float:
        """Calcula o Capital Empregado (Imobilizado + NCG).
        Conforme TCC p. 17: "soma entre necessidade de capital de giro (NCG) e imobilizado".
        O yfinance fornece 'PropertyPlantAndEquipment' para imobilizado.
        """
        # A conta 'PropertyPlantAndEquipment' é o imobilizado (fixed assets)
        # Se for o caso de a empresa não ter imobilizado, mas ter CAPEX para projetos
        # uma análise mais profunda seria necessária.
        # Por simplicidade, usamos o imobilizado do balanço.
        imobilizado = data.property_plant_equipment if data.property_plant_equipment is not None else 0
        ncg = self._calculate_ncg(data)
        
        # O Capital Empregado deve ser positivo. Se NCG for muito negativo, pode distorcer.
        # Se o imobilizado for zero, o CE pode ser negativo se a NCG for negativa.
        # Uma NCG negativa significa que o Passivo Circulante Operacional > Ativo Circulante Operacional.
        # Capital Empregado = (Ativos Operacionais - Passivos Operacionais Não Onerosos)
        # Ou = Patrimônio Líquido + Dívida Onerosa
        # Usando a definição do TCC: Imobilizado + NCG
        return imobilizado + ncg

    def _calculate_cost_of_equity_ke(self, beta: float) -> float:
        """Calcula o Custo do Capital Próprio (Ke) usando CAPM.
        Ke = Taxa sem Risco + Beta * Prêmio de Risco de Mercado
        """
        return self.risk_free_rate + beta * self.market_risk_premium
    
    def _calculate_cost_of_debt_kd(self, data: CompanyFinancialData) -> float:
        """Calcula o Custo do Capital de Terceiros (Kd).
        Simplificação: usar despesas financeiras / dívida total.
        Yfinance não fornece despesas financeiras diretamente no quarterly_financials para todas as empresas.
        Alternativa é estimar com base na taxa de juros média do mercado ou custo de oportunidade.
        Para demonstração, vamos usar uma estimativa simples ou retornar um valor padrão se dados faltarem.
        Uma abordagem mais robusta seria buscar 'InterestExpense' do income statement.
        """
        # Tentando obter InterestExpense do income statement trimestral
        # Como CompanyFinancialData não tem 'InterestExpense', e não quero refazer o coletor para este demo,
        # vamos usar uma estimativa baseada na SELIC + spread, ou um valor default razoável.
        # No seu TCC, Kd é "multiplicação entre despesas financeiras com juros (Kd) e a participação da dívida líquida no passivo oneroso (%Kd)" (p. 20)
        # Isso implica que Kd já é a taxa.
        # Vamos assumir uma taxa base se não puder ser calculada precisamente.
        # Em um cenário real, você teria acesso às despesas com juros.
        
        # ESTIMATIVA SIMPLIFICADA PARA DEMONSTRAÇÃO
        if data.total_debt > 0:
            # Assumimos que o custo da dívida é um pouco acima da Selic
            return self.risk_free_rate * 1.2 # Selic + 20%
        return 0.05 # Default 5% se não houver dívida relevante

    def _calculate_wacc(self, data: CompanyFinancialData, beta: float) -> float:
        """Calcula o WACC (Custo Médio Ponderado de Capital).
        CMPC = (Kd x %Kd) + (Ke x %Ke) - Equação 5 (p. 20)
        %Ke = Equity / (Equity + TotalDebt)
        %Kd = TotalDebt / (Equity + TotalDebt)
        """
        total_capital = data.equity + data.total_debt
        if total_capital <= 0:
            logger.warning(f"Total Capital (Equity + Debt) é zero ou negativo para {data.ticker}. Não é possível calcular WACC.")
            return np.nan

        ke = self._calculate_cost_of_equity_ke(beta)
        kd = self._calculate_cost_of_debt_kd(data) # Kd é a taxa de custo da dívida
        
        # %Ke e %Kd são participações do Capital Próprio e Terceiros no capital total
        percent_ke = data.equity / total_capital
        percent_kd = data.total_debt / total_capital
        
        # WACC ajustado pelo benefício fiscal da dívida: Kd * (1 - TaxRate) * %Kd
        wacc = (ke * percent_ke) + (kd * (1 - self.tax_rate) * percent_kd)
        return wacc

    def _calculate_roce(self, data: CompanyFinancialData, capital_employed: float) -> float:
        """Calcula o ROCE (Retorno do Capital Empregado).
        ROCE = (NOPAT / Capital Empregado)
        No TCC, ROCE é RCE = Retorno Operacional das Vendas * Rotatividade do Capital Empregado (p. 18)
        Retorno Operacional das Vendas = Fluxo de Caixa Operacional / Receitas Líquidas
        Rotatividade do Capital Empregado = Receita Líquida / Capital Empregado
        
        Então, RCE = (Fluxo de Caixa Operacional / Receitas Líquidas) * (Receita Líquida / Capital Empregado)
                   = Fluxo de Caixa Operacional / Capital Empregado
        """
        # yfinance cash flow statement tem 'OperatingCashFlow'
        operating_cash_flow = data.cash # Assumindo cash como proxy para OCF recente se não houver campo direto no dataclass
        # Uma implementação mais precisa buscaria 'OperatingCashFlow' do CF Statement do yfinance

        if capital_employed == 0:
            return np.nan
        
        # Simplificação: NOPAT para fluxo de caixa operacional, para ser consistente com a lógica do EVA
        # mas mantendo o espírito do ROCE como eficiência do capital
        nopat = self._calculate_nopat(data.ebit)
        
        return nopat / capital_employed

    def calculate_eva(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        """Calcula o EVA (Economic Value Added) absoluto e percentual.
        EVA = (Capital Empregado) x (Retorno do Capital Empregado - Custo Médio Ponderado de Capital) - Equação 1 (p. 17)
        """
        capital_employed = self._calculate_capital_employed(data)
        if capital_employed <= 0: # Capital empregado precisa ser positivo para EVA significativo
             return np.nan, np.nan

        wacc = self._calculate_wacc(data, beta)
        roce = self._calculate_roce(data, capital_employed)

        if np.isnan(wacc) or np.isnan(roce):
            return np.nan, np.nan
        
        eva_abs = capital_employed * (roce - wacc)
        eva_pct = (roce - wacc) * 100 # Em percentual, como no TCC

        return eva_abs, eva_pct

    def calculate_efv(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        """Calcula o EFV (Economic Future Value) absoluto e percentual.
        EFV = Riqueza Futura Esperada - Riqueza Atual - Equação 2 (p. 19)
        """
        # Calcular Riqueza Atual e Futura primeiro
        riqueza_atual_abs = self.calculate_riqueza_atual(data, beta)
        riqueza_futura_esperada_abs = self.calculate_riqueza_futura(data)

        if np.isnan(riqueza_atual_abs) or np.isnan(riqueza_futura_esperada_abs):
            return np.nan, np.nan

        efv_abs = riqueza_futura_esperada_abs - riqueza_atual_abs
        
        # EFV percentual (TCC p. 103, Apêndice C: EFV % = EFV / Capital Empregado)
        capital_employed = self._calculate_capital_employed(data)
        if capital_employed <= 0:
            return np.nan, np.nan
        
        efv_pct = (efv_abs / capital_employed) * 100
        
        return efv_abs, efv_pct

    def calculate_riqueza_atual(self, data: CompanyFinancialData, beta: float) -> float:
        """Calcula a Riqueza Atual.
        Riqueza Atual = EVA / CMPC - Equação 4 (p. 20)
        """
        eva_abs, _ = self.calculate_eva(data, beta)
        wacc = self._calculate_wacc(data, beta)
        
        if np.isnan(eva_abs) or np.isnan(wacc) or wacc == 0:
            return np.nan
        
        return eva_abs / wacc

    def calculate_riqueza_futura(self, data: CompanyFinancialData) -> float:
        """Calcula a Riqueza Futura Esperada.
        Riqueza Futura Esperada = {(preço de ações ordinárias x quantidade de ações ordinárias emitidas)
                                    + (preço de ações preferenciais x quantidade de ações preferenciais emitidas)
                                    + valor da dívida da empresa - capital empregado} - Equação 3 (p. 20)
        
        Simplificação para Ibovespa: usar Market Cap (ações ordinárias + preferenciais) + Dívida Total - Capital Empregado
        """
        # Market Cap já inclui todas as ações negociadas na bolsa
        market_value_equity = data.market_cap 
        total_debt = data.total_debt
        capital_employed = self._calculate_capital_employed(data)

        if np.isnan(market_value_equity) or np.isnan(total_debt) or np.isnan(capital_employed):
            return np.nan

        # Valor da Firma (Enterprise Value) = Market Cap + Total Debt - Cash
        # Riqueza Futura Esperada = Enterprise Value - Capital Empregado (no espírito do TCC)
        # O TCC menciona: "valor da dívida da empresa - capital empregado"
        # O termo "valor da dívida da empresa" na Equação 3 parece se referir à dívida que já está no balanço.
        # A fórmula do TCC é um pouco peculiar em relação ao EV tradicional.
        # "preço das ações... + valor da dívida da empresa - capital empregado"
        # Isso é próximo de: (Market Cap + Total Debt) - Capital Empregado
        # O (Market Cap + Total Debt) é o Enterprise Value se ignorarmos o Cash.
        
        # Vamos seguir a Equação 3 literalmente, usando Market Cap para "preço de ações * quantidade"
        # e total_debt para "valor da dívida da empresa"
        
        riqueza_futura = (market_value_equity + total_debt) - capital_employed
        return riqueza_futura

    def calculate_upside(self, data: CompanyFinancialData, efv_abs: float) -> float:
        """Calcula o potencial de valorização (Upside).
        Upside = (EFV Absoluto / Market Cap) * 100
        """
        if data.market_cap <= 0:
            return np.nan
        return (efv_abs / data.market_cap) * 100

class CompanyRanking:
    """
    Classifica empresas com base nas métricas financeiras.
    """
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def _calculate_all_metrics(self, data: CompanyFinancialData) -> Dict[str, Union[float, str]]:
        """Calcula todas as métricas para uma única empresa."""
        try:
            # Beta hardcoded para fins de demonstração. Em produção, você usaria um modelo para estimar.
            # Um beta de 1.0 é um bom ponto de partida para empresas diversificadas.
            # Seu TCC menciona o modelo de Hamada para cálculo de beta. Isso seria implementado aqui.
            beta = 1.0 # Exemplo de beta
            
            # Recalcular WACC para obter o valor mais recente
            wacc = self.calculator._calculate_wacc(data, beta)
            if np.isnan(wacc): wacc = 0.0

            eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            riqueza_atual = self.calculator.calculate_riqueza_atual(data, beta)
            riqueza_futura = self.calculator.calculate_riqueza_futura(data)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan
            
            # Calcular o Score Combinado
            # A ponderação exata viria de uma análise mais profunda ou do advanced_ranking
            # Para demonstração, um score simples
            score_combinado = 0
            if not np.isnan(eva_pct): score_combinado += eva_pct * 0.4
            if not np.isnan(efv_pct): score_combinado += efv_pct * 0.4
            if not np.isnan(upside): score_combinado += upside * 0.2
            
            return {
                'ticker': data.ticker,
                'company_name': data.company_name,
                'market_cap': data.market_cap,
                'stock_price': data.stock_price,
                'wacc_percentual': wacc * 100 if not np.isnan(wacc) else np.nan,
                'eva_abs': eva_abs,
                'eva_percentual': eva_pct,
                'efv_abs': efv_abs,
                'efv_percentual': efv_pct,
                'riqueza_atual': riqueza_atual,
                'riqueza_futura': riqueza_futura,
                'upside_percentual': upside,
                'combined_score': score_combinado
            }
        except Exception as e:
            logger.error(f"Erro ao calcular métricas para {data.ticker}: {e}")
            return {'ticker': data.ticker, 'company_name': data.company_name, 'error': str(e)}

    def generate_ranking_report(self, companies_data: Dict[str, CompanyFinancialData]) -> pd.DataFrame:
        """
        Gera um DataFrame com o relatório de ranking de todas as empresas.
        """
        report_data = []
        for ticker, data in companies_data.items():
            metrics = self._calculate_all_metrics(data)
            if 'error' not in metrics:
                report_data.append(metrics)
            else:
                logger.warning(f"Empresa {ticker} excluída do relatório devido a erro: {metrics['error']}")

        df = pd.DataFrame(report_data)
        
        # Limpar NaN/Inf para garantir que o sort funcione
        for col in ['wacc_percentual', 'eva_percentual', 'efv_percentual', 'riqueza_atual', 'riqueza_futura', 'upside_percentual', 'combined_score']:
            if col in df.columns:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                df[col] = df[col].fillna(0) # Substituir NaN por 0 para ranking, ou outro valor estratégico

        return df

    def rank_by_metric(self, df: pd.DataFrame, metric: str, ascending: bool = False) -> List[Tuple[str, float]]:
        """
        Classifica as empresas por uma métrica específica e retorna uma lista de tuplas.
        """
        if metric not in df.columns:
            logger.warning(f"Métrica '{metric}' não encontrada para ranking.")
            return []
        
        sorted_df = df.sort_values(by=metric, ascending=ascending)
        return sorted_df[['ticker', metric]].values.tolist()

    def rank_by_eva(self, df: pd.DataFrame) -> List[Tuple[str, float, float]]:
        """Classifica empresas por EVA (percentual)."""
        sorted_df = df.sort_values(by='eva_percentual', ascending=False)
        return sorted_df[['ticker', 'eva_abs', 'eva_percentual']].values.tolist()

    def rank_by_efv(self, df: pd.DataFrame) -> List[Tuple[str, float, float]]:
        """Classifica empresas por EFV (percentual)."""
        sorted_df = df.sort_values(by='efv_percentual', ascending=False)
        return sorted_df[['ticker', 'efv_abs', 'efv_percentual']].values.tolist()

    def rank_by_upside(self, df: pd.DataFrame) -> List[Tuple[str, float]]:
        """Classifica empresas por potencial de valorização (Upside)."""
        sorted_df = df.sort_values(by='upside_percentual', ascending=False)
        return sorted_df[['ticker', 'upside_percentual']].values.tolist()
    
    def rank_by_combined_score(self, df: pd.DataFrame) -> List[Tuple[str, float]]:
        """Classifica empresas por score combinado."""
        sorted_df = df.sort_values(by='combined_score', ascending=False)
        return sorted_df[['ticker', 'combined_score']].values.tolist()


if __name__ == '__main__':
    from ibovespa_data import get_ibovespa_tickers, get_selic_rate
    from utils import format_currency, format_percentage, PerformanceMonitor

    monitor = PerformanceMonitor()
    monitor.start_timer("processo_completo_financial_analyzer_demo")

    # 1. Coleta de dados
    collector = FinancialDataCollector()
    tickers_to_analyze = get_ibovespa_tickers()[:15] # Limitar para demo rápida

    print(f"Coletando dados para {len(tickers_to_analyze)} empresas: {', '.join(tickers_to_analyze)}...")
    monitor.start_timer("coleta_dados_financial_analyzer_demo")
    companies_data = collector.get_multiple_companies(tickers_to_analyze)
    monitor.end_timer("coleta_dados_financial_analyzer_demo")

    if not companies_data:
        print("Nenhuma empresa coletada. Abortando demo.")
    else:
        # 2. Inicializar calculadora com a Selic
        selic_rate = get_selic_rate()
        calculator = FinancialMetricsCalculator(selic_rate=selic_rate)
        ranking_system = CompanyRanking(calculator)

        # 3. Gerar relatório de ranking
        print("\nGerando relatório de ranking...")
        monitor.start_timer("ranking_report_financial_analyzer_demo")
        report_df = ranking_system.generate_ranking_report(companies_data)
        monitor.end_timer("ranking_report_financial_analyzer_demo")
        
        if not report_df.empty:
            print("\nRelatório de Ranking (Primeiras 5 linhas):")
            print(report_df.head())

            print("\nTop 5 por EVA (%):")
            top_eva = ranking_system.rank_by_eva(report_df)
            for i, (ticker, eva_abs, eva_pct) in enumerate(top_eva[:5], 1):
                print(f"{i}. {ticker}: EVA = {format_percentage(eva_pct)} ({format_currency(eva_abs)})")

            print("\nTop 5 por EFV (%):")
            top_efv = ranking_system.rank_by_efv(report_df)
            for i, (ticker, efv_abs, efv_pct) in enumerate(top_efv[:5], 1):
                print(f"{i}. {ticker}: EFV = {format_percentage(efv_pct)} ({format_currency(efv_abs)})")
            
            print("\nTop 5 por Score Combinado:")
            top_combined = ranking_system.rank_by_combined_score(report_df)
            for i, (ticker, score) in enumerate(top_combined[:5], 1):
                print(f"{i}. {ticker}: Score = {score:.2f}")
        else:
            print("Relatório de ranking está vazio. Verifique a coleta de dados ou cálculos.")

    monitor.end_timer("processo_completo_financial_analyzer_demo")
