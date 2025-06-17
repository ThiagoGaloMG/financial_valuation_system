# backend/src/financial_analyzer.py

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from typing import Dict, List, Optional, Tuple
import logging
import time

# --- CORREÇÃO PRINCIPAL ---
# Importa a classe do novo arquivo dedicado e os dados de exemplo.
from financial_analyzer_dataclass import CompanyFinancialData
from sample_data import sample_financial_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# A definição da classe CompanyFinancialData foi movida para seu próprio arquivo.

class FinancialDataCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_company_data(self, ticker: str) -> Optional[CompanyFinancialData]:
        """
        Tenta coletar dados via yfinance. Se falhar por qualquer motivo (erro, timeout, dados vazios),
        recorre aos dados de exemplo (fallback).
        """
        logger.info(f"Tentando coletar dados para {ticker} via yfinance...")
        try:
            stock = yf.Ticker(ticker, session=self.session)
            info = stock.info
            
            # Validação crucial: se não houver 'marketCap', a coleta falhou.
            if not info or info.get('marketCap') is None:
                raise ValueError(f"Informações básicas (info) inválidas ou não encontradas para {ticker}")

            financials = stock.quarterly_financials
            balance_sheet = stock.quarterly_balance_sheet
            cash_flow = stock.quarterly_cash_flow

            if financials.empty or balance_sheet.empty or cash_flow.empty:
                raise ValueError(f"Uma ou mais demonstrações financeiras estão vazias para {ticker}")

            latest_date = financials.columns[0]
            fin_data, bs_data, cf_data = financials[latest_date], balance_sheet[latest_date], cash_flow[latest_date]
            
            logger.info(f"Sucesso ao coletar dados para {ticker} via yfinance.")
            return CompanyFinancialData(
                ticker=ticker,
                company_name=info.get('longName', ticker),
                market_cap=info.get('marketCap', 0),
                stock_price=info.get('currentPrice', info.get('previousClose', 0)),
                shares_outstanding=info.get('sharesOutstanding', 0),
                revenue=fin_data.get('TotalRevenue', 0),
                ebit=fin_data.get('Ebit', 0),
                net_income=fin_data.get('NetIncome', 0),
                depreciation_amortization=cf_data.get('DepreciationAndAmortization', 0),
                capex=abs(cf_data.get('CapitalExpenditures', 0) or 0),
                total_assets=bs_data.get('TotalAssets', 0),
                total_debt=bs_data.get('TotalDebt', 0),
                equity=bs_data.get('TotalStockholderEquity', 0),
                current_assets=bs_data.get('TotalCurrentAssets', 0),
                current_liabilities=bs_data.get('TotalCurrentLiabilities', 0),
                cash=bs_data.get('CashAndCashEquivalents', 0),
                accounts_receivable=bs_data.get('NetReceivables', 0),
                inventory=bs_data.get('Inventory', 0),
                accounts_payable=bs_data.get('AccountsPayable', 0),
                property_plant_equipment=bs_data.get('PropertyPlantAndEquipment', 0),
                sector=info.get('sector', 'N/A')
            )
        except Exception as e:
            logger.warning(f"Falha ao coletar dados para {ticker} via yfinance: {e}. Usando dados de exemplo se disponível.")
            return sample_financial_data.get(ticker)

    def get_multiple_companies(self, tickers: List[str]) -> Dict[str, CompanyFinancialData]:
        companies_data = {}
        for ticker in tickers:
            data = self.get_company_data(ticker)
            if data:
                companies_data[ticker] = data
        
        # Se, após todas as tentativas, nenhum dado foi coletado, usamos os dados de exemplo.
        if not companies_data:
            logger.error("Falha ao coletar dados para TODOS os tickers. Retornando o conjunto completo de dados de exemplo.")
            return sample_financial_data

        return companies_data

class FinancialMetricsCalculator:
    def __init__(self, selic_rate: Optional[float] = None):
        self.tax_rate = 0.34
        self.risk_free_rate = (selic_rate / 100) if selic_rate else 0.10
        self.market_risk_premium = 0.06

    def _calculate_nopat(self, ebit: float) -> float:
        return ebit * (1 - self.tax_rate)

    def _calculate_ncg(self, data: CompanyFinancialData) -> float:
        return (data.accounts_receivable or 0) + (data.inventory or 0) - (data.accounts_payable or 0)

    def _calculate_capital_employed(self, data: CompanyFinancialData) -> float:
        imobilizado = data.property_plant_equipment or 0
        ncg = self._calculate_ncg(data)
        return imobilizado + ncg

    def _calculate_cost_of_equity_ke(self, beta: float) -> float:
        return self.risk_free_rate + beta * self.market_risk_premium
    
    def _calculate_cost_of_debt_kd(self, data: CompanyFinancialData) -> float:
        return self.risk_free_rate * 1.2 if data.total_debt > 0 else 0.05

    def _calculate_wacc(self, data: CompanyFinancialData, beta: float) -> float:
        total_capital = (data.equity or 0) + (data.total_debt or 0)
        if total_capital <= 0: return np.nan
        ke = self._calculate_cost_of_equity_ke(beta)
        kd = self._calculate_cost_of_debt_kd(data)
        percent_ke = (data.equity or 0) / total_capital
        percent_kd = (data.total_debt or 0) / total_capital
        return (ke * percent_ke) + (kd * (1 - self.tax_rate) * percent_kd)

    def _calculate_roce(self, data: CompanyFinancialData, capital_employed: float) -> float:
        if capital_employed <= 0: return np.nan
        nopat = self._calculate_nopat(data.ebit or 0)
        return nopat / capital_employed

    def calculate_eva(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        capital_employed = self._calculate_capital_employed(data)
        if capital_employed <= 0: return np.nan, np.nan
        wacc = self._calculate_wacc(data, beta)
        roce = self._calculate_roce(data, capital_employed)
        if np.isnan(wacc) or np.isnan(roce): return np.nan, np.nan
        eva_abs = capital_employed * (roce - wacc)
        eva_pct = (roce - wacc) * 100
        return eva_abs, eva_pct

    def calculate_riqueza_atual(self, data: CompanyFinancialData, beta: float) -> float:
        eva_abs, _ = self.calculate_eva(data, beta)
        wacc = self._calculate_wacc(data, beta)
        if np.isnan(eva_abs) or np.isnan(wacc) or wacc == 0: return np.nan
        return eva_abs / wacc

    def calculate_riqueza_futura(self, data: CompanyFinancialData) -> float:
        market_value_equity = data.market_cap 
        total_debt = data.total_debt
        capital_employed = self._calculate_capital_employed(data)
        if np.isnan(market_value_equity) or np.isnan(total_debt) or np.isnan(capital_employed): return np.nan
        return (market_value_equity + total_debt) - capital_employed

    def calculate_efv(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        riqueza_atual_abs = self.calculate_riqueza_atual(data, beta)
        riqueza_futura_esperada_abs = self.calculate_riqueza_futura(data)
        if np.isnan(riqueza_atual_abs) or np.isnan(riqueza_futura_esperada_abs): return np.nan, np.nan
        efv_abs = riqueza_futura_esperada_abs - riqueza_atual_abs
        capital_employed = self._calculate_capital_employed(data)
        if capital_employed <= 0: return efv_abs, np.nan
        efv_pct = (efv_abs / capital_employed) * 100
        return efv_abs, efv_pct

    def calculate_upside(self, data: CompanyFinancialData, efv_abs: float) -> float:
        if data.market_cap <= 0: return np.nan
        return (efv_abs / data.market_cap) * 100

class CompanyRanking:
    def __init__(self, calculator: FinancialMetricsCalculator):
        self.calculator = calculator

    def _calculate_all_metrics(self, data: CompanyFinancialData) -> Dict:
        try:
            beta = 1.0
            wacc = self.calculator._calculate_wacc(data, beta)
            eva_abs, eva_pct = self.calculator.calculate_eva(data, beta)
            efv_abs, efv_pct = self.calculator.calculate_efv(data, beta)
            riqueza_atual = self.calculator.calculate_riqueza_atual(data, beta)
            riqueza_futura = self.calculator.calculate_riqueza_futura(data)
            upside = self.calculator.calculate_upside(data, efv_abs) if not np.isnan(efv_abs) else np.nan
            
            score_combinado = (np.nan_to_num(eva_pct) * 0.4) + (np.nan_to_num(efv_pct) * 0.4) + (np.nan_to_num(upside) * 0.2)
            
            return {
                'ticker': data.ticker, 'company_name': data.company_name, 'market_cap': data.market_cap,
                'stock_price': data.stock_price, 'wacc_percentual': wacc * 100 if not np.isnan(wacc) else np.nan,
                'eva_abs': eva_abs, 'eva_percentual': eva_pct, 'efv_abs': efv_abs, 'efv_percentual': efv_pct,
                'riqueza_atual': riqueza_atual, 'riqueza_futura': riqueza_futura, 'upside_percentual': upside,
                'combined_score': score_combinado
            }
        except Exception as e:
            logger.error(f"Erro ao calcular métricas para {data.ticker}: {e}")
            return {'ticker': data.ticker, 'company_name': data.company_name, 'error': str(e)}

    def generate_ranking_report(self, companies_data: Dict[str, CompanyFinancialData]) -> pd.DataFrame:
        report_data = [self._calculate_all_metrics(data) for data in companies_data.values() if data]
        df = pd.DataFrame([d for d in report_data if 'error' not in d])
        for col in ['wacc_percentual', 'eva_percentual', 'efv_percentual', 'upside_percentual', 'combined_score']:
            if col in df.columns:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)
        return df
