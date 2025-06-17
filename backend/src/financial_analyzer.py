# backend/src/financial_analyzer.py

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from typing import Dict, List, Optional, Tuple
import logging
import time
from datetime import datetime

# Importa a classe do dataclass e dados de exemplo
from financial_analyzer_dataclass import CompanyFinancialData
from sample_data import sample_financial_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class FinancialDataCollector:
    def __init__(self):
        self.retry_wait_seconds = 10
        self.max_retries = 10

    def get_company_data(self, ticker: str) -> Optional[CompanyFinancialData]:
        """
        Coleta dados via yfinance: histórico de preços e alguns campos fundamentais.
        Em caso de falha, usa dados de exemplo.
        """
        logger.info(f"Coletando dados para {ticker} via yfinance...")
        # 1) Baixar histórico de preços para cálculos de retorno
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            hist = yf.download(ticker, start="2011-01-01", end=end_date, progress=False)
            if hist is None or hist.empty or "Close" not in hist.columns:
                raise ValueError("Histórico de preços indisponível")
            hist['return'] = hist['Close'].pct_change()
            return_mean = hist['return'].mean()
            return_std = hist['return'].std()
            latest_price = hist['Close'].iloc[-1]
        except Exception as e:
            logger.warning(f"Falha ao baixar histórico para {ticker}: {e}")
            base = sample_financial_data.get(ticker)
            if base:
                # Ajusta price e retornos se possível
                try:
                    base.stock_price = getattr(base, 'stock_price', None) or None
                    setattr(base, 'return_mean', None)
                    setattr(base, 'return_std', None)
                except Exception:
                    pass
                return base
            return None

        # 2) Coletar dados fundamentais com retry
        info = {}
        for attempt in range(self.max_retries):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                if info and info.get('marketCap') is not None:
                    break
                else:
                    raise ValueError("Campo marketCap ausente")
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1}: falha ao obter info para {ticker}: {e}")
                time.sleep(self.retry_wait_seconds * (attempt+1))
        if not info or info.get('marketCap') is None:
            logger.warning(f"Dados fundamentais indisponíveis para {ticker}. Usando fallback se disponível.")
            base = sample_financial_data.get(ticker)
            if base:
                base.stock_price = latest_price
                setattr(base, 'return_mean', return_mean)
                setattr(base, 'return_std', return_std)
                return base
            return None

        # 3) Extrair campos essenciais de info
        try:
            company_name = info.get('longName', ticker)
            market_cap = info.get('marketCap', 0)
            stock_price = info.get('currentPrice', latest_price)
            total_debt = info.get('totalDebt', 0) or 0
            equity = info.get('totalStockholderEquity', 0) or 0
            sector = info.get('sector', 'N/A')

            data_obj = CompanyFinancialData(
                ticker=ticker,
                company_name=company_name,
                market_cap=market_cap,
                stock_price=stock_price,
                shares_outstanding=info.get('sharesOutstanding', None),
                revenue=info.get('totalRevenue', None),
                ebit=info.get('ebit', None),
                net_income=info.get('netIncome', None),
                depreciation_amortization=info.get('depreciationAndAmortization', None),
                capex=abs(info.get('capitalExpenditures', 0) or 0),
                total_assets=info.get('totalAssets', None),
                total_debt=total_debt,
                equity=equity,
                current_assets=info.get('totalCurrentAssets', None),
                current_liabilities=info.get('totalCurrentLiabilities', None),
                cash=info.get('totalCash', None),
                accounts_receivable=info.get('netReceivables', None),
                inventory=info.get('inventory', None),
                accounts_payable=info.get('accountsPayable', None),
                property_plant_equipment=info.get('propertyPlant', None),
                sector=sector
            )
            # Atribuir retornos calculados
            setattr(data_obj, 'return_mean', return_mean)
            setattr(data_obj, 'return_std', return_std)
            return data_obj
        except Exception as e:
            logger.warning(f"Erro ao montar CompanyFinancialData para {ticker}: {e}")
            return None

    def get_multiple_companies(self, tickers: List[str]) -> Dict[str, CompanyFinancialData]:
        companies_data = {}
        for ticker in tickers:
            data = self.get_company_data(ticker)
            if data:
                companies_data[ticker] = data
            # Prevenção 429: pausa breve
            time.sleep(0.5)
        if not companies_data:
            logger.error("Falha ao coletar dados para TODOS os tickers. Retornando dados de exemplo.")
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
        return (getattr(data, 'accounts_receivable', 0) or 0) + (getattr(data, 'inventory', 0) or 0) - (getattr(data, 'accounts_payable', 0) or 0)

    def _calculate_capital_employed(self, data: CompanyFinancialData) -> float:
        imobilizado = getattr(data, 'property_plant_equipment', 0) or 0
        ncg = self._calculate_ncg(data)
        return imobilizado + ncg

    def _calculate_cost_of_equity_ke(self, beta: float) -> float:
        return self.risk_free_rate + beta * self.market_risk_premium

    def _calculate_cost_of_debt_kd(self, data: CompanyFinancialData) -> float:
        return self.risk_free_rate * 1.2 if getattr(data, 'total_debt', 0) and data.total_debt > 0 else 0.05

    def _calculate_wacc(self, data: CompanyFinancialData, beta: float) -> float:
        total_capital = ((getattr(data, 'equity', 0) or 0) + (getattr(data, 'total_debt', 0) or 0))
        if total_capital <= 0:
            return np.nan
        ke = self._calculate_cost_of_equity_ke(beta)
        kd = self._calculate_cost_of_debt_kd(data)
        percent_ke = (getattr(data, 'equity', 0) or 0) / total_capital
        percent_kd = (getattr(data, 'total_debt', 0) or 0) / total_capital
        return (ke * percent_ke) + (kd * (1 - self.tax_rate) * percent_kd)

    def _calculate_roce(self, data: CompanyFinancialData, capital_employed: float) -> float:
        if capital_employed <= 0:
            return np.nan
        nopat = self._calculate_nopat(getattr(data, 'ebit', 0) or 0)
        return nopat / capital_employed

    def calculate_eva(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        capital_employed = self._calculate_capital_employed(data)
        if capital_employed <= 0:
            return np.nan, np.nan
        wacc = self._calculate_wacc(data, beta)
        roce = self._calculate_roce(data, capital_employed)
        if np.isnan(wacc) or np.isnan(roce):
            return np.nan, np.nan
        eva_abs = capital_employed * (roce - wacc)
        eva_pct = (roce - wacc) * 100
        return eva_abs, eva_pct

    def calculate_riqueza_atual(self, data: CompanyFinancialData, beta: float) -> float:
        eva_abs, _ = self.calculate_eva(data, beta)
        wacc = self._calculate_wacc(data, beta)
        if np.isnan(eva_abs) or np.isnan(wacc) or wacc == 0:
            return np.nan
        return eva_abs / wacc

    def calculate_riqueza_futura(self, data: CompanyFinancialData) -> float:
        market_value_equity = getattr(data, 'market_cap', np.nan)
        total_debt = getattr(data, 'total_debt', np.nan)
        capital_employed = self._calculate_capital_employed(data)
        if np.isnan(market_value_equity) or np.isnan(total_debt) or np.isnan(capital_employed):
            return np.nan
        return (market_value_equity + total_debt) - capital_employed

    def calculate_efv(self, data: CompanyFinancialData, beta: float) -> Tuple[float, float]:
        riqueza_atual_abs = self.calculate_riqueza_atual(data, beta)
        riqueza_futura_esperada_abs = self.calculate_riqueza_futura(data)
        if np.isnan(riqueza_atual_abs) or np.isnan(riqueza_futura_esperada_abs):
            return np.nan, np.nan
        efv_abs = riqueza_futura_esperada_abs - riqueza_atual_abs
        capital_employed = self._calculate_capital_employed(data)
        if capital_employed <= 0:
            return efv_abs, np.nan
        efv_pct = (efv_abs / capital_employed) * 100
        return efv_abs, efv_pct

    def calculate_upside(self, data: CompanyFinancialData, efv_abs: float) -> float:
        market_cap = getattr(data, 'market_cap', np.nan)
        if market_cap <= 0 or np.isnan(market_cap):
            return np.nan
        return (efv_abs / market_cap) * 100

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
        report_data = [self._calculate_all_metrics(data) for data in companies_data.values() if data]
        df = pd.DataFrame([d for d in report_data if 'error' not in d])
        for col in ['wacc_percentual', 'eva_percentual', 'efv_percentual', 'upside_percentual', 'combined_score']:
            if col in df.columns:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)
        return df
