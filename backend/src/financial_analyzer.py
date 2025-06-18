# backend/src/financial_analyzer.py

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any # <--- CORREÇÃO: 'Tuple' e 'Any' adicionados.

import yfinance as yf
import pandas as pd
import numpy as np
import requests

# CORREÇÃO: A importação do dataclass foi mantida como estava no seu arquivo.
from financial_analyzer_dataclass import CompanyFinancialData
from sample_data import sample_financial_data

# Configuração do logger
logger = logging.getLogger(__name__)

# --- Configurações de Coleta de Dados ---
# OTIMIZAÇÃO: As constantes foram movidas para cá para evitar importações problemáticas de `src/__init__`.
YFINANCE_REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 15


class FinancialDataCollector:
    """
    Coleta dados financeiros de empresas usando a API yfinance.
    Inclui lógica de retentativas e delays para lidar com instabilidades da API.
    """
    def __init__(self):
        self.max_retries = int(os.getenv("YFINANCE_MAX_RETRIES", "3"))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_company_financials(self, ticker: str) -> Optional[CompanyFinancialData]:
        """
        Busca os dados financeiros para um ticker específico.
        Retorna um objeto CompanyFinancialData ou None em caso de falha.
        """
        logger.info(f"Coletando dados para o ticker: {ticker}")
        time.sleep(YFINANCE_REQUEST_DELAY) # Delay para não sobrecarregar a API yfinance

        for attempt in range(self.max_retries):
            try:
                stock = yf.Ticker(ticker, session=self.session)
                info = stock.info
                
                # Validação mínima para garantir que a empresa foi encontrada
                if not info or info.get('quoteType') != 'EQUITY':
                    logger.warning(f"Dados inválidos ou não é uma ação para {ticker}. Pulando.")
                    return None

                # Coleta de dados com valores padrão para evitar KeyErrors
                financials = {
                    'ticker': ticker,
                    'company_name': info.get('longName', ticker),
                    'market_cap': info.get('marketCap', 0),
                    'stock_price': info.get('currentPrice') or info.get('regularMarketPrice') or 0,
                    'shares_outstanding': info.get('sharesOutstanding', 0),
                    'revenue': info.get('totalRevenue', 0),
                    'ebit': info.get('ebit', 0),
                    'net_income': info.get('netIncomeToCommon', 0),
                    'sector': info.get('sector', 'N/A'),
                }

                # Dados de balanço e fluxo de caixa (podem falhar)
                balance_sheet = stock.balance_sheet
                cash_flow = stock.cashflow
                
                financials['total_assets'] = balance_sheet.loc['Total Assets'].iloc[0] if not balance_sheet.empty and 'Total Assets' in balance_sheet.index else 0
                financials['total_debt'] = info.get('totalDebt', 0)
                financials['equity'] = balance_sheet.loc['Stockholders Equity'].iloc[0] if not balance_sheet.empty and 'Stockholders Equity' in balance_sheet.index else 0
                financials['current_assets'] = balance_sheet.loc['Current Assets'].iloc[0] if not balance_sheet.empty and 'Current Assets' in balance_sheet.index else 0
                financials['current_liabilities'] = balance_sheet.loc['Current Liabilities'].iloc[0] if not balance_sheet.empty and 'Current Liabilities' in balance_sheet.index else 0
                financials['cash'] = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0] if not balance_sheet.empty and 'Cash And Cash Equivalents' in balance_sheet.index else 0
                financials['accounts_receivable'] = balance_sheet.loc['Receivables'].iloc[0] if not balance_sheet.empty and 'Receivables' in balance_sheet.index else 0
                financials['inventory'] = balance_sheet.loc['Inventory'].iloc[0] if not balance_sheet.empty and 'Inventory' in balance_sheet.index else 0
                financials['accounts_payable'] = balance_sheet.loc['Payables And Accrued Expenses'].iloc[0] if not balance_sheet.empty and 'Payables And Accrued Expenses' in balance_sheet.index else 0
                
                financials['depreciation_amortization'] = cash_flow.loc['Depreciation And Amortization'].iloc[0] if not cash_flow.empty and 'Depreciation And Amortization' in cash_flow.index else 0
                financials['capex'] = cash_flow.loc['Capital Expenditure'].iloc[0] if not cash_flow.empty and 'Capital Expenditure' in cash_flow.index else 0
                
                financials['property_plant_equipment'] = balance_sheet.loc['Net PPE'].iloc[0] if not balance_sheet.empty and 'Net PPE' in balance_sheet.index else 0

                # Substitui valores NaN por 0 para consistência
                for key, value in financials.items():
                    if pd.isna(value):
                        financials[key] = 0

                return CompanyFinancialData(**financials)

            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou para {ticker}: {e}. Tentando novamente em {self.max_retries}s...")
                time.sleep(self.max_retries)
        
        logger.error(f"Falha ao coletar dados para {ticker} após {self.max_retries} tentativas. Usando dados de exemplo se disponíveis.")
        return sample_financial_data.get(ticker)


class FinancialMetricsCalculator:
    """
    Calcula todas as métricas financeiras (WACC, EVA, EFV, etc.)
    com base nos dados coletados.
    """
    def __init__(self, selic_rate: float, tax_rate: float = 0.34, market_risk_premium: float = 0.05):
        self.selic_rate = selic_rate / 100
        self.tax_rate = tax_rate
        self.market_risk_premium = market_risk_premium

    def _calculate_capital_employed(self, data: CompanyFinancialData) -> float:
        return (data.equity or 0) + (data.total_debt or 0)

    def _calculate_wacc(self, data: CompanyFinancialData, beta: float) -> float:
        cost_of_equity = self.selic_rate + beta * self.market_risk_premium
        cost_of_debt = 0.06 # Assumindo um custo de dívida padrão de 6%
        
        equity_weight = (data.equity or 0) / self._calculate_capital_employed(data)
        debt_weight = (data.total_debt or 0) / self._calculate_capital_employed(data)

        if np.isnan(equity_weight) or np.isnan(debt_weight): return np.nan

        wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - self.tax_rate))
        return wacc

    # CORREÇÃO: A anotação de tipo 'Tuple' foi importada e pode ser usada.
    def calculate_eva(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        nopat = (data.ebit or 0) * (1 - self.tax_rate)
        capital_employed = self._calculate_capital_employed(data)
        wacc = self._calculate_wacc(data, beta)

        if capital_employed <= 0 or np.isnan(wacc):
            return 0.0, 0.0

        eva_abs = nopat - (capital_employed * wacc)
        eva_pct = (eva_abs / capital_employed) * 100 if capital_employed > 0 else 0.0
        return eva_abs, eva_pct

    def calculate_riqueza_atual(self, data: CompanyFinancialData, beta: float) -> float:
        eva_abs, _ = self.calculate_eva(data, beta)
        wacc = self._calculate_wacc(data, beta)
        if np.isnan(eva_abs) or np.isnan(wacc) or wacc == 0:
            return np.nan
        return eva_abs / wacc

    def calculate_riqueza_futura(self, data: CompanyFinancialData) -> float:
        return (data.market_cap or 0) - self._calculate_capital_employed(data)

    def calculate_efv(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        riqueza_atual_abs = self.calculate_riqueza_atual(data, beta)
        riqueza_futura_esperada_abs = self.calculate_riqueza_futura(data)
        efv_abs = riqueza_futura_esperada_abs - riqueza_atual_abs
        capital_employed = self._calculate_capital_employed(data)
        
        efv_pct = (efv_abs / capital_employed) * 100 if capital_employed > 0 else 0.0
        return efv_abs, efv_pct

    def calculate_upside(self, data: CompanyFinancialData, beta: float) -> float:
        riqueza_atual = self.calculate_riqueza_atual(data, beta)
        capital_employed = self._calculate_capital_employed(data)
        
        fair_value = riqueza_atual + capital_employed
        if data.market_cap is None or data.market_cap <= 0:
            return np.nan
            
        upside_pct = ((fair_value / data.market_cap) - 1) * 100
        return upside_pct


class CompanyRanking:
    """
    Cria um ranking das empresas com base em um score combinado.
    """
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def rank_companies(self, companies_data: List[CompanyFinancialData]) -> List[Dict[str, Any]]:
        results = []
        for data in companies_data:
            try:
                beta = 1.0 # Beta padrão para simplificação
                eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
                efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
                upside = self.calculator.calculate_upside(data, beta)
                
                # Cálculo do Score
                score = (eva_pct * 0.4) + (efv_pct * 0.3) + (upside * 0.3)

                results.append({
                    'ticker': data.ticker,
                    'company_name': data.company_name,
                    'metrics': {
                        'combined_score': score,
                        'eva_percentual': eva_pct,
                        'efv_percentual': efv_pct,
                        'upside_percentual': upside,
                        'wacc_percentual': self.calculator._calculate_wacc(data, beta) * 100,
                        'market_cap': data.market_cap,
                        'stock_price': data.stock_price,
                        'raw_data': vars(data) # Inclui os dados brutos para referência
                    }
                })
            except Exception as e:
                logger.error(f"Erro ao rankear {data.ticker}: {e}")
                
        # Ordena pelo score combinado, do maior para o menor
        ranked_results = sorted(results, key=lambda x: x['metrics']['combined_score'], reverse=True)
        return ranked_results
