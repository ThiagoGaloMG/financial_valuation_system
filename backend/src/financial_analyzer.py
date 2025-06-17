# backend/src/financial_analyzer.py

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

import yfinance as yf
import pandas as pd
import numpy as np
import requests

from financial_analyzer_dataclass import CompanyFinancialData
from sample_data import sample_financial_data
from src import YFINANCE_REQUEST_DELAY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format='%(asctime)s [%(levelname)s] - %(message)s')


class FinancialDataCollector:
    def __init__(self):
        # Base retry/backoff settings
        try:
            self.retry_wait_seconds = float(os.getenv("YFINANCE_RETRY_WAIT_SECONDS", "1"))
        except ValueError:
            self.retry_wait_seconds = 1.0
        try:
            self.max_retries = int(os.getenv("YFINANCE_MAX_RETRIES", "3"))
        except ValueError:
            self.max_retries = 3
        # Delay entre chamadas de tickers para mitigar 429
        try:
            self.request_delay = float(os.getenv("YFINANCE_REQUEST_DELAY", str(YFINANCE_REQUEST_DELAY)))
        except ValueError:
            self.request_delay = YFINANCE_REQUEST_DELAY
        # Session for requests if needed
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0'
        })

    def get_company_data(self, ticker: str) -> Optional[CompanyFinancialData]:
        logger.info(f"Coletando dados para {ticker} via yfinance...")
        # 1) Histórico de preços com retry/backoff
        end_date = datetime.now().strftime("%Y-%m-%d")
        hist = None
        for attempt in range(self.max_retries):
            try:
                hist = yf.download(ticker, start="2011-01-01", end=end_date, progress=False)
                if hist is None or hist.empty or "Close" not in hist.columns:
                    raise ValueError("Histórico de preços vazio ou indisponível")
                break
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1}/{self.max_retries} download histórico {ticker} falhou: {e}")
                time.sleep(self.retry_wait_seconds * (attempt + 1))
        if hist is None or hist.empty:
            logger.warning(f"Todas as tentativas de histórico falharam para {ticker}. Usando fallback se disponível.")
            base = sample_financial_data.get(ticker)
            return base
        # Processar histórico: retorno e estatísticas
        hist['return'] = hist['Close'].pct_change()
        try:
            return_mean = hist['return'].mean()
            return_std = hist['return'].std()
        except Exception:
            return_mean = None
            return_std = None
        latest_price = hist['Close'].iloc[-1]

        # 2) Info fundamental com retry/backoff
        info = {}
        for attempt in range(self.max_retries):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                if info and info.get('marketCap') is not None:
                    break
                else:
                    raise ValueError("Campo marketCap ausente ou inválido")
            except Exception as e:
                logger.warning(f"Tentativa {attempt+1}/{self.max_retries} obter info {ticker} falhou: {e}")
                time.sleep(self.retry_wait_seconds * (attempt + 1))
        if not info or info.get('marketCap') is None:
            logger.warning(f"Dados fundamentais indisponíveis para {ticker}. Usando fallback se disponível.")
            base = sample_financial_data.get(ticker)
            if base:
                try:
                    base.stock_price = latest_price
                    setattr(base, 'return_mean', return_mean)
                    setattr(base, 'return_std', return_std)
                except Exception:
                    pass
                return base
            return None

        # 3) Extrair campos essenciais e criar CompanyFinancialData
        try:
            company_name = info.get('longName', ticker)
            market_cap = info.get('marketCap', 0)
            stock_price = info.get('currentPrice', latest_price)
            shares_outstanding = info.get('sharesOutstanding', None)
            revenue = info.get('totalRevenue', None)
            ebit = info.get('ebit', None)
            net_income = info.get('netIncome', None)
            depreciation_amortization = info.get('depreciationAndAmortization', None)
            capex = abs(info.get('capitalExpenditures', 0) or 0)
            total_assets = info.get('totalAssets', None)
            total_debt = info.get('totalDebt', 0) or 0
            equity = info.get('totalStockholderEquity', None) or 0
            current_assets = info.get('totalCurrentAssets', None)
            current_liabilities = info.get('totalCurrentLiabilities', None)
            cash = info.get('totalCash', None)
            accounts_receivable = info.get('netReceivables', None)
            inventory = info.get('inventory', None)
            accounts_payable = info.get('accountsPayable', None)
            property_plant_equipment = info.get('propertyPlant', None)
            sector = info.get('sector', None)

            data_obj = CompanyFinancialData(
                ticker=ticker,
                company_name=company_name,
                market_cap=market_cap,
                stock_price=stock_price,
                shares_outstanding=shares_outstanding,
                revenue=revenue,
                ebit=ebit,
                net_income=net_income,
                depreciation_amortization=depreciation_amortization,
                capex=capex,
                total_assets=total_assets,
                total_debt=total_debt,
                equity=equity,
                current_assets=current_assets,
                current_liabilities=current_liabilities,
                cash=cash,
                accounts_receivable=accounts_receivable,
                inventory=inventory,
                accounts_payable=accounts_payable,
                property_plant_equipment=property_plant_equipment,
                sector=sector
            )
            # Atributos adicionais
            setattr(data_obj, 'return_mean', return_mean)
            setattr(data_obj, 'return_std', return_std)
            return data_obj
        except Exception as e:
            logger.warning(f"Erro ao montar CompanyFinancialData para {ticker}: {e}")
            return None

    def get_multiple_companies(self, tickers: List[str]) -> Dict[str, CompanyFinancialData]:
        companies_data: Dict[str, CompanyFinancialData] = {}
        for ticker in tickers:
            data = self.get_company_data(ticker)
            if data:
                companies_data[ticker] = data
            # Delay entre chamadas para evitar bloqueio 429
            time.sleep(self.request_delay)
        if not companies_data:
            logger.error("Falha em coletar dados para todos os tickers. Retornando fallback de exemplo.")
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
        return self.risk_free_rate * 1.2 if data.total_debt and data.total_debt > 0 else 0.05

    def _calculate_wacc(self, data: CompanyFinancialData, beta: float) -> float:
        total_capital = (data.equity or 0) + (data.total_debt or 0)
        if total_capital <= 0:
            return np.nan
        ke = self._calculate_cost_of_equity_ke(beta)
        kd = self._calculate_cost_of_debt_kd(data)
        percent_ke = (data.equity or 0) / total_capital
        percent_kd = (data.total_debt or 0) / total_capital
        return (ke * percent_ke) + (kd * (1 - self.tax_rate) * percent_kd)

    def _calculate_roce(self, data: CompanyFinancialData, capital_employed: float) -> float:
        if capital_employed <= 0:
            return np.nan
        nopat = self._calculate_nopat(data.ebit or 0)
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
        market_value_equity = data.market_cap or 0
        total_debt = data.total_debt or 0
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
        if not data.market_cap or data.market_cap <= 0:
            return np.nan
        return (efv_abs / data.market_cap) * 100
