# backend/src/financial_analyzer_improved.py
# Versão melhorada do financial_analyzer usando brapi.dev

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import requests

from financial_analyzer_dataclass import CompanyFinancialData
from sample_data import sample_financial_data
from brapi_data_collector import BrapiDataCollector

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format='%(asctime)s [%(levelname)s] - %(message)s')


class FinancialDataCollector:
    def __init__(self):
        # Configurações de retry/backoff
        try:
            self.retry_wait_seconds = float(os.getenv("BRAPI_RETRY_WAIT_SECONDS", "1"))
        except ValueError:
            self.retry_wait_seconds = 1.0
        try:
            self.max_retries = int(os.getenv("BRAPI_MAX_RETRIES", "3"))
        except ValueError:
            self.max_retries = 3

        # Configurações de timeout
        try:
            self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        except ValueError:
            self.request_timeout = 30

        # Delay entre requisições para evitar rate limiting
        try:
            self.request_delay = float(os.getenv("BRAPI_REQUEST_DELAY", "1.0"))
        except ValueError:
            self.request_delay = 1.0

        # Inicializar o coletor brapi.dev
        self.brapi_collector = BrapiDataCollector()

    def collect_company_data(self, ticker: str) -> Optional[CompanyFinancialData]:
        """
        Coleta dados financeiros de uma empresa usando brapi.dev.
        
        Args:
            ticker: Código da ação (ex: 'PETR4')
            
        Returns:
            CompanyFinancialData ou None se não conseguir coletar
        """
        try:
            # Remover .SA do ticker se presente (brapi.dev usa formato sem .SA)
            clean_ticker = ticker.replace('.SA', '')
            
            logger.info(f"Coletando dados para o ticker: {clean_ticker}")
            
            # Usar o coletor brapi.dev
            data = self.brapi_collector.collect_company_data(clean_ticker)
            
            if not data:
                logger.warning(f"Nenhum dado retornado para {clean_ticker}")
                return None
            
            # Converter para CompanyFinancialData
            company_data = self._convert_brapi_to_company_data(clean_ticker, data)
            
            # Delay entre requisições
            time.sleep(self.request_delay)
            
            return company_data
            
        except Exception as e:
            logger.error(f"Erro ao coletar dados para {ticker}: {e}")
            return None

    def _convert_brapi_to_company_data(self, ticker: str, brapi_data: dict) -> CompanyFinancialData:
        """
        Converte dados do brapi.dev para CompanyFinancialData.
        
        Args:
            ticker: Código da ação
            brapi_data: Dados retornados pelo brapi.dev
            
        Returns:
            CompanyFinancialData
        """
        try:
            # Extrair dados básicos
            quote_data = brapi_data.get('quote', {})
            fundamentals = brapi_data.get('fundamentals', {})
            
            # Dados básicos da empresa
            company_name = quote_data.get('longName', ticker)
            sector = fundamentals.get('sector', 'N/A')
            
            # Preço da ação
            stock_price = quote_data.get('regularMarketPrice', 0)
            
            # Market Cap
            market_cap = quote_data.get('marketCap', 0)
            if not market_cap and stock_price:
                shares_outstanding = fundamentals.get('sharesOutstanding', 0)
                if shares_outstanding:
                    market_cap = stock_price * shares_outstanding
            
            # Dados financeiros do balanço
            balance_sheet = fundamentals.get('balanceSheet', {})
            income_statement = fundamentals.get('incomeStatement', {})
            
            # Total de ativos
            total_assets = balance_sheet.get('totalAssets', 0)
            
            # Patrimônio líquido
            total_equity = balance_sheet.get('totalStockholderEquity', 0)
            
            # Lucro líquido
            net_income = income_statement.get('netIncome', 0)
            
            # Receita total
            total_revenue = income_statement.get('totalRevenue', 0)
            
            # Dívida total
            total_debt = balance_sheet.get('totalDebt', 0)
            if not total_debt:
                # Tentar calcular como soma de dívidas de curto e longo prazo
                short_debt = balance_sheet.get('shortLongTermDebt', 0)
                long_debt = balance_sheet.get('longTermDebt', 0)
                total_debt = short_debt + long_debt
            
            # Múltiplos
            pe_ratio = fundamentals.get('trailingPE', 0)
            pb_ratio = fundamentals.get('priceToBook', 0)
            
            # Criar objeto CompanyFinancialData
            company_data = CompanyFinancialData(
                ticker=ticker,
                company_name=company_name,
                sector=sector,
                stock_price=float(stock_price) if stock_price else 0.0,
                market_cap=float(market_cap) if market_cap else 0.0,
                total_assets=float(total_assets) if total_assets else 0.0,
                total_equity=float(total_equity) if total_equity else 0.0,
                net_income=float(net_income) if net_income else 0.0,
                total_revenue=float(total_revenue) if total_revenue else 0.0,
                total_debt=float(total_debt) if total_debt else 0.0,
                pe_ratio=float(pe_ratio) if pe_ratio else 0.0,
                pb_ratio=float(pb_ratio) if pb_ratio else 0.0,
                data_quality_score=self._calculate_data_quality_score(brapi_data)
            )
            
            logger.info(f"Dados convertidos com sucesso para {ticker}")
            return company_data
            
        except Exception as e:
            logger.error(f"Erro ao converter dados do brapi.dev para {ticker}: {e}")
            # Retornar dados básicos em caso de erro
            return CompanyFinancialData(
                ticker=ticker,
                company_name=ticker,
                sector="N/A",
                stock_price=0.0,
                market_cap=0.0,
                total_assets=0.0,
                total_equity=0.0,
                net_income=0.0,
                total_revenue=0.0,
                total_debt=0.0,
                pe_ratio=0.0,
                pb_ratio=0.0,
                data_quality_score=0.0
            )

    def _calculate_data_quality_score(self, brapi_data: dict) -> float:
        """
        Calcula um score de qualidade dos dados (0-1).
        
        Args:
            brapi_data: Dados retornados pelo brapi.dev
            
        Returns:
            Score de qualidade entre 0 e 1
        """
        try:
            score = 0.0
            max_score = 10.0
            
            quote_data = brapi_data.get('quote', {})
            fundamentals = brapi_data.get('fundamentals', {})
            balance_sheet = fundamentals.get('balanceSheet', {})
            income_statement = fundamentals.get('incomeStatement', {})
            
            # Verificar campos essenciais
            if quote_data.get('regularMarketPrice'):
                score += 1.0  # Preço da ação
            if quote_data.get('marketCap'):
                score += 1.0  # Market Cap
            if balance_sheet.get('totalAssets'):
                score += 1.0  # Total de ativos
            if balance_sheet.get('totalStockholderEquity'):
                score += 1.0  # Patrimônio líquido
            if income_statement.get('netIncome'):
                score += 1.0  # Lucro líquido
            if income_statement.get('totalRevenue'):
                score += 1.0  # Receita total
            if balance_sheet.get('totalDebt') or (balance_sheet.get('shortLongTermDebt') and balance_sheet.get('longTermDebt')):
                score += 1.0  # Dívida total
            if fundamentals.get('trailingPE'):
                score += 1.0  # P/E ratio
            if fundamentals.get('priceToBook'):
                score += 1.0  # P/B ratio
            if quote_data.get('longName'):
                score += 1.0  # Nome da empresa
            
            return score / max_score
            
        except Exception as e:
            logger.error(f"Erro ao calcular score de qualidade: {e}")
            return 0.0

    def collect_multiple_companies(self, tickers: List[str]) -> Dict[str, CompanyFinancialData]:
        """
        Coleta dados de múltiplas empresas.
        
        Args:
            tickers: Lista de códigos de ações
            
        Returns:
            Dicionário com ticker como chave e CompanyFinancialData como valor
        """
        results = {}
        total_tickers = len(tickers)
        
        logger.info(f"Iniciando coleta de dados para {total_tickers} empresas")
        
        for i, ticker in enumerate(tickers, 1):
            time.sleep(2)
            try:
                logger.info(f"Processando {i}/{total_tickers}: {ticker}")
                
                company_data = self.collect_company_data(ticker)
                if company_data:
                    results[ticker] = company_data
                    logger.info(f"Sucesso: {ticker} - Score: {company_data.data_quality_score:.2f}")
                else:
                    logger.warning(f"Falha ao coletar dados para {ticker}")
                
            except Exception as e:
                logger.error(f"Erro ao processar {ticker}: {e}")
                continue
        
        logger.info(f"Coleta concluída: {len(results)}/{total_tickers} empresas processadas")
        return results


# Manter as outras classes inalteradas
class FinancialMetricsCalculator:
    """
    Calculadora de métricas financeiras (EVA, EFV, WACC, etc.).
    Esta classe permanece inalterada pois não depende da fonte de dados.
    """
    
    def __init__(self, selic_rate: float = 0.1465):
        self.selic_rate = selic_rate
        self.risk_free_rate = selic_rate
        
    def calculate_wacc(self, company_data: CompanyFinancialData, market_risk_premium: float = 0.06) -> float:
        """
        Calcula o WACC (Weighted Average Cost of Capital).
        
        Args:
            company_data: Dados financeiros da empresa
            market_risk_premium: Prêmio de risco de mercado (padrão 6%)
            
        Returns:
            WACC como decimal (ex: 0.12 para 12%)
        """
        try:
            # Valores básicos
            market_value_equity = company_data.market_cap
            market_value_debt = company_data.total_debt
            total_value = market_value_equity + market_value_debt
            
            if total_value <= 0:
                return self.risk_free_rate + market_risk_premium
            
            # Pesos
            weight_equity = market_value_equity / total_value
            weight_debt = market_value_debt / total_value
            
            # Custo do capital próprio (CAPM simplificado)
            # Beta assumido como 1.0 para simplificação
            beta = 1.0
            cost_of_equity = self.risk_free_rate + beta * market_risk_premium
            
            # Custo da dívida (simplificado)
            cost_of_debt = self.risk_free_rate + 0.03  # Spread de 3%
            
            # Taxa de imposto (assumida como 34% para Brasil)
            tax_rate = 0.34
            
            # WACC
            wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
            
            return wacc
            
        except Exception as e:
            logger.error(f"Erro ao calcular WACC para {company_data.ticker}: {e}")
            return self.risk_free_rate + market_risk_premium

    def calculate_eva(self, company_data: CompanyFinancialData, wacc: float) -> Tuple[float, float]:
        """
        Calcula o EVA (Economic Value Added).
        
        Args:
            company_data: Dados financeiros da empresa
            wacc: Custo médio ponderado de capital
            
        Returns:
            Tupla (EVA absoluto, EVA percentual)
        """
        try:
            # NOPAT (Net Operating Profit After Taxes)
            # Simplificação: usar lucro líquido
            nopat = company_data.net_income
            
            # Capital investido
            invested_capital = company_data.total_assets
            
            if invested_capital <= 0:
                return 0.0, 0.0
            
            # Custo do capital
            capital_cost = invested_capital * wacc
            
            # EVA absoluto
            eva_abs = nopat - capital_cost
            
            # EVA percentual
            eva_perc = (eva_abs / invested_capital) * 100 if invested_capital > 0 else 0.0
            
            return eva_abs, eva_perc
            
        except Exception as e:
            logger.error(f"Erro ao calcular EVA para {company_data.ticker}: {e}")
            return 0.0, 0.0

    def calculate_efv(self, company_data: CompanyFinancialData, wacc: float, growth_rate: float = 0.03) -> Tuple[float, float]:
        """
        Calcula o EFV (Economic Future Value).
        
        Args:
            company_data: Dados financeiros da empresa
            wacc: Custo médio ponderado de capital
            growth_rate: Taxa de crescimento esperada (padrão 3%)
            
        Returns:
            Tupla (EFV absoluto, EFV percentual)
        """
        try:
            # EVA atual
            eva_abs, _ = self.calculate_eva(company_data, wacc)
            
            # EFV = EVA * (1 + g) / (WACC - g)
            if wacc <= growth_rate:
                # Evitar divisão por zero ou negativo
                efv_abs = eva_abs * 10  # Multiplicador conservador
            else:
                efv_abs = eva_abs * (1 + growth_rate) / (wacc - growth_rate)
            
            # EFV percentual
            invested_capital = company_data.total_assets
            efv_perc = (efv_abs / invested_capital) * 100 if invested_capital > 0 else 0.0
            
            return efv_abs, efv_perc
            
        except Exception as e:
            logger.error(f"Erro ao calcular EFV para {company_data.ticker}: {e}")
            return 0.0, 0.0

    def calculate_wealth_metrics(self, company_data: CompanyFinancialData, wacc: float) -> Tuple[float, float]:
        """
        Calcula métricas de riqueza (atual e futura).
        
        Args:
            company_data: Dados financeiros da empresa
            wacc: Custo médio ponderado de capital
            
        Returns:
            Tupla (Riqueza atual, Riqueza futura)
        """
        try:
            # Riqueza atual = Market Cap
            current_wealth = company_data.market_cap
            
            # Riqueza futura = Market Cap + EFV
            efv_abs, _ = self.calculate_efv(company_data, wacc)
            future_wealth = current_wealth + efv_abs
            
            return current_wealth, future_wealth
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas de riqueza para {company_data.ticker}: {e}")
            return company_data.market_cap, company_data.market_cap

    def calculate_upside(self, company_data: CompanyFinancialData, wacc: float) -> float:
        """
        Calcula o potencial de valorização (upside).
        
        Args:
            company_data: Dados financeiros da empresa
            wacc: Custo médio ponderado de capital
            
        Returns:
            Upside percentual
        """
        try:
            current_wealth, future_wealth = self.calculate_wealth_metrics(company_data, wacc)
            
            if current_wealth <= 0:
                return 0.0
            
            upside = ((future_wealth - current_wealth) / current_wealth) * 100
            return upside
            
        except Exception as e:
            logger.error(f"Erro ao calcular upside para {company_data.ticker}: {e}")
            return 0.0


class CompanyRanking:
    """
    Sistema de ranking de empresas baseado em múltiplas métricas.
    """
    
    def __init__(self, calculator):
        self.calculator = calculator  # Armazena o calculator para uso futuro, se necessário
        self.weights = {
            'eva_percentual': 0.25,
            'efv_percentual': 0.25,
            'upside': 0.20,
            'data_quality': 0.15,
            'market_cap': 0.10,
            'pe_ratio': 0.05
        }
    
    def calculate_combined_score(self, metrics: Dict[str, float]) -> float:
        """
        Calcula um score combinado baseado em múltiplas métricas.
        
        Args:
            metrics: Dicionário com as métricas calculadas
            
        Returns:
            Score combinado (0-100)
        """
        try:
            score = 0.0
            
            # Normalizar e ponderar cada métrica
            eva_score = self._normalize_eva(metrics.get('eva_percentual', 0))
            efv_score = self._normalize_efv(metrics.get('efv_percentual', 0))
            upside_score = self._normalize_upside(metrics.get('upside', 0))
            quality_score = metrics.get('data_quality_score', 0) * 100
            cap_score = self._normalize_market_cap(metrics.get('market_cap', 0))
            pe_score = self._normalize_pe_ratio(metrics.get('pe_ratio', 0))
            
            # Aplicar pesos
            score = (
                eva_score * self.weights['eva_percentual'] +
                efv_score * self.weights['efv_percentual'] +
                upside_score * self.weights['upside'] +
                quality_score * self.weights['data_quality'] +
                cap_score * self.weights['market_cap'] +
                pe_score * self.weights['pe_ratio']
            )
            
            return min(100.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"Erro ao calcular score combinado: {e}")
            return 0.0
    
    def _normalize_eva(self, eva_perc: float) -> float:
        """Normaliza EVA percentual para escala 0-100."""
        if eva_perc > 20:
            return 100.0
        elif eva_perc > 0:
            return 50.0 + (eva_perc / 20.0) * 50.0
        else:
            return max(0.0, 50.0 + eva_perc * 2.5)
    
    def _normalize_efv(self, efv_perc: float) -> float:
        """Normaliza EFV percentual para escala 0-100."""
        if efv_perc > 50:
            return 100.0
        elif efv_perc > 0:
            return 50.0 + (efv_perc / 50.0) * 50.0
        else:
            return max(0.0, 50.0 + efv_perc * 1.0)
    
    def _normalize_upside(self, upside: float) -> float:
        """Normaliza upside para escala 0-100."""
        if upside > 100:
            return 100.0
        elif upside > 0:
            return upside
        else:
            return 0.0
    
    def _normalize_market_cap(self, market_cap: float) -> float:
        """Normaliza market cap para escala 0-100."""
        if market_cap > 100_000_000_000:  # > 100B
            return 100.0
        elif market_cap > 10_000_000_000:  # > 10B
            return 80.0
        elif market_cap > 1_000_000_000:   # > 1B
            return 60.0
        elif market_cap > 100_000_000:     # > 100M
            return 40.0
        else:
            return 20.0
    
    def _normalize_pe_ratio(self, pe_ratio: float) -> float:
        """Normaliza P/E ratio para escala 0-100 (menor é melhor)."""
        if pe_ratio <= 0:
            return 0.0
        elif pe_ratio < 10:
            return 100.0
        elif pe_ratio < 20:
            return 80.0
        elif pe_ratio < 30:
            return 60.0
        else:
            return 40.0
