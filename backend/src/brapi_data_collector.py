# backend/src/brapi_data_collector.py
"""
Coletor de dados financeiros usando a API brapi.dev
Alternativa ao yfinance para dados mais confiáveis do mercado brasileiro
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrapiDataCollector:
    """
    Coletor de dados financeiros usando a API brapi.dev
    """
    
    def __init__(self, api_token: str = None):
        """
        Inicializa o coletor de dados da brapi.dev
        
        Args:
            api_token: Token de autenticação da brapi.dev
        """
        self.base_url = "https://brapi.dev/api"
        self.api_token = api_token
        self.headers = {
            "Content-Type": "application/json"
        }
        
        if api_token:
            self.headers["Authorization"] = f"Bearer {api_token}"
        
        # Rate limiting
        self.request_delay = 1.0  # Delay entre requisições em segundos
        self.last_request_time = 0
        
        # Cache para evitar requisições desnecessárias
        self.cache = {}
        self.cache_ttl = 300  # 5 minutos
    
    def _make_request(self, url: str, params: Dict = None) -> Dict:
        """
        Faz uma requisição HTTP com rate limiting e tratamento de erros
        
        Args:
            url: URL da requisição
            params: Parâmetros da requisição
            
        Returns:
            Resposta JSON da API
        """
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Rate limit atingido. Aguardando...")
                time.sleep(60)  # Aguarda 1 minuto
                return self._make_request(url, params)  # Retry
            else:
                logger.error(f"Erro na API: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            return None
    
    def get_stock_quote(self, ticker: str) -> Dict:
        """
        Obtém cotação atual de uma ação
        
        Args:
            ticker: Código da ação (ex: PETR4)
            
        Returns:
            Dados da cotação
        """
        # Verifica cache
        cache_key = f"quote_{ticker}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]['data']
        
        url = f"{self.base_url}/quote/{ticker}"
        data = self._make_request(url)
        
        if data and 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            self._cache_data(cache_key, result)
            return result
        
        return None
    
    def get_fundamental_data(self, ticker: str) -> Dict:
        """
        Obtém dados fundamentalistas completos de uma ação
        
        Args:
            ticker: Código da ação (ex: PETR4)
            
        Returns:
            Dados fundamentalistas (Balanço, DRE, Fluxo de Caixa)
        """
        # Verifica cache
        cache_key = f"fundamental_{ticker}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]['data']
        
        modules = [
            'balanceSheetHistory',
            'incomeStatementHistory',
            'cashFlowStatementHistory'
        ]
        
        url = f"{self.base_url}/quote/{ticker}"
        params = {
            'modules': ','.join(modules),
            'fundamental': 'true'
        }
        
        data = self._make_request(url, params)
        
        if data and 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            self._cache_data(cache_key, result)
            return result
        
        return None
    
    def get_historical_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """
        Obtém dados históricos de preços
        
        Args:
            ticker: Código da ação
            period: Período (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            DataFrame com dados históricos
        """
        url = f"{self.base_url}/quote/{ticker}"
        params = {
            'range': period,
            'interval': '1d'
        }
        
        data = self._make_request(url, params)
        
        if data and 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            if 'historicalDataPrice' in result:
                df = pd.DataFrame(result['historicalDataPrice'])
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                return df
        
        return pd.DataFrame()
    
    def get_ibovespa_companies(self) -> List[str]:
        """
        Obtém lista de empresas do Ibovespa
        
        Returns:
            Lista de tickers das empresas do Ibovespa
        """
        # Lista atualizada das empresas do Ibovespa (principais)
        ibovespa_tickers = [
            'PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'ABEV3', 'BBAS3', 'WEGE3',
            'RENT3', 'LREN3', 'MGLU3', 'SUZB3', 'RAIL3', 'USIM5', 'CSNA3',
            'GOAU4', 'CCRO3', 'EMBR3', 'CIEL3', 'JBSS3', 'BEEF3', 'MRFG3',
            'BRDT3', 'AZUL4', 'GOLL4', 'CYRE3', 'MRVE3', 'EZTC3', 'MULT3',
            'GGBR4', 'KLBN11', 'SUZANO', 'FIBR3', 'ELET3', 'ELET6', 'CMIG4',
            'CPFE3', 'EGIE3', 'ENGI11', 'TAEE11', 'VIVT3', 'TIMP3', 'TIMS3',
            'RADL3', 'RAIA3', 'PCAR3', 'FLRY3', 'QUAL3', 'HAPV3', 'PLAN4',
            'GNDI3', 'ODPV3', 'NTCO3', 'LWSA3', 'CASH3', 'PETZ3', 'VVAR3',
            'SBSP3', 'SAPR11', 'CSAN3', 'UGPA3', 'SMTO3', 'YDUQ3', 'COGN3',
            'ARZZ3', 'SOMA3', 'GMAT3', 'PRIO3', 'RECV3', 'EVEN3', 'JHSF3',
            'BRML3', 'BRAP4', 'SLCE3', 'ALPA4', 'CMIN3', 'BRKM5', 'POMO4',
            'TOTS3', 'DXCO3', 'IRBR3', 'SULA11', 'PSSA3', 'CVCB3', 'HYPE3'
        ]
        
        return ibovespa_tickers
    
    def collect_company_data(self, ticker: str) -> Dict:
        """
        Coleta dados completos de uma empresa para análise EVA/EFV
        
        Args:
            ticker: Código da ação
            
        Returns:
            Dicionário com todos os dados necessários
        """
        logger.info(f"Coletando dados para {ticker}")
        
        # Dados básicos de cotação
        quote_data = self.get_stock_quote(ticker)
        if not quote_data:
            logger.warning(f"Não foi possível obter cotação para {ticker}")
            return None
        
        # Dados fundamentalistas
        fundamental_data = self.get_fundamental_data(ticker)
        
        # Estrutura dos dados coletados
        company_data = {
            'ticker': ticker,
            'company_name': quote_data.get('longName', quote_data.get('shortName', ticker)),
            'currency': quote_data.get('currency', 'BRL'),
            
            # Dados de mercado
            'stock_price': quote_data.get('regularMarketPrice'),
            'market_cap': quote_data.get('marketCap'),
            'shares_outstanding': quote_data.get('sharesOutstanding'),
            'volume': quote_data.get('regularMarketVolume'),
            
            # Múltiplos básicos
            'pe_ratio': quote_data.get('priceEarnings'),
            'price_to_book': quote_data.get('priceToBook'),
            'earnings_per_share': quote_data.get('earningsPerShare'),
            'book_value_per_share': quote_data.get('bookValuePerShare'),
            
            # Dados fundamentalistas (se disponíveis)
            'fundamental_data': fundamental_data,
            
            # Timestamp da coleta
            'collected_at': datetime.now().isoformat()
        }
        
        # Extrai dados do balanço patrimonial mais recente
        if fundamental_data and 'balanceSheetHistory' in fundamental_data:
            balance_sheets = fundamental_data['balanceSheetHistory']
            if balance_sheets and len(balance_sheets) > 0:
                latest_balance = balance_sheets[0]  # Mais recente
                
                company_data.update({
                    'total_assets': latest_balance.get('totalAssets'),
                    'total_liabilities': latest_balance.get('totalLiab'),
                    'stockholder_equity': latest_balance.get('totalStockholderEquity'),
                    'total_debt': latest_balance.get('totalDebt'),
                    'cash_and_equivalents': latest_balance.get('cash'),
                    'current_assets': latest_balance.get('totalCurrentAssets'),
                    'current_liabilities': latest_balance.get('totalCurrentLiabilities')
                })
        
        # Extrai dados da DRE mais recente
        if fundamental_data and 'incomeStatementHistory' in fundamental_data:
            income_statements = fundamental_data['incomeStatementHistory']
            if income_statements and len(income_statements) > 0:
                latest_income = income_statements[0]  # Mais recente
                
                company_data.update({
                    'total_revenue': latest_income.get('totalRevenue'),
                    'net_income': latest_income.get('netIncome'),
                    'operating_income': latest_income.get('operatingIncome'),
                    'ebitda': latest_income.get('ebitda'),
                    'gross_profit': latest_income.get('grossProfit'),
                    'interest_expense': latest_income.get('interestExpense')
                })
        
        # Extrai dados do fluxo de caixa mais recente
        if fundamental_data and 'cashFlowStatementHistory' in fundamental_data:
            cash_flows = fundamental_data['cashFlowStatementHistory']
            if cash_flows and len(cash_flows) > 0:
                latest_cash_flow = cash_flows[0]  # Mais recente
                
                company_data.update({
                    'operating_cash_flow': latest_cash_flow.get('operatingCashFlow'),
                    'free_cash_flow': latest_cash_flow.get('freeCashFlow'),
                    'capital_expenditures': latest_cash_flow.get('capitalExpenditures')
                })
        
        return company_data
    
    def collect_ibovespa_data(self) -> List[Dict]:
        """
        Coleta dados de todas as empresas do Ibovespa
        
        Returns:
            Lista com dados de todas as empresas
        """
        companies = self.get_ibovespa_companies()
        all_data = []
        
        logger.info(f"Iniciando coleta de dados para {len(companies)} empresas do Ibovespa")
        
        for i, ticker in enumerate(companies, 1):
            logger.info(f"Processando {ticker} ({i}/{len(companies)})")
            
            try:
                company_data = self.collect_company_data(ticker)
                if company_data:
                    all_data.append(company_data)
                else:
                    logger.warning(f"Dados não coletados para {ticker}")
                    
            except Exception as e:
                logger.error(f"Erro ao coletar dados de {ticker}: {e}")
                continue
        
        logger.info(f"Coleta concluída. {len(all_data)} empresas processadas com sucesso.")
        return all_data
    
    def _is_cached(self, key: str) -> bool:
        """Verifica se os dados estão em cache e ainda são válidos"""
        if key not in self.cache:
            return False
        
        cache_time = self.cache[key]['timestamp']
        return (time.time() - cache_time) < self.cache_ttl
    
    def _cache_data(self, key: str, data: any):
        """Armazena dados no cache"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

# Função de conveniência para uso direto
def create_brapi_collector(api_token: str = None) -> BrapiDataCollector:
    """
    Cria uma instância do coletor brapi.dev
    
    Args:
        api_token: Token da API (opcional para uso básico)
        
    Returns:
        Instância do BrapiDataCollector
    """
    return BrapiDataCollector(api_token)

# Exemplo de uso
if __name__ == "__main__":
    # Teste básico
    collector = BrapiDataCollector()
    
    # Testa coleta de uma empresa
    data = collector.collect_company_data("PETR4")
    if data:
        print(f"Dados coletados para {data['company_name']}")
        print(f"Market Cap: R$ {data.get('market_cap', 'N/A'):,}")
        print(f"Preço: R$ {data.get('stock_price', 'N/A')}")
    else:
        print("Falha na coleta de dados")
