# backend/src/ibovespa_data_improved.py
"""
Versão melhorada do coletor de dados do Ibovespa usando brapi.dev
Substitui o yfinance por uma fonte mais confiável
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from brapi_data_collector import BrapiDataCollector

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IbovespaDataImproved:
    """
    Coletor de dados melhorado para empresas do Ibovespa usando brapi.dev
    """
    
    def __init__(self):
        """Inicializa o coletor de dados"""
        # Token da API brapi.dev (deve ser configurado via variável de ambiente)
        api_token = os.getenv('BRAPI_API_TOKEN')
        
        if not api_token:
            logger.warning("Token da brapi.dev não configurado. Usando modo gratuito com limitações.")
        
        self.collector = BrapiDataCollector(api_token)
        
        # Lista atualizada das empresas do Ibovespa
        self.ibovespa_companies = [
            'PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'ABEV3', 'BBAS3', 'WEGE3',
            'RENT3', 'LREN3', 'MGLU3', 'SUZB3', 'RAIL3', 'USIM5', 'CSNA3',
            'GOAU4', 'CCRO3', 'EMBR3', 'CIEL3', 'JBSS3', 'BEEF3', 'MRFG3',
            'BRDT3', 'AZUL4', 'GOLL4', 'CYRE3', 'MRVE3', 'EZTC3', 'MULT3',
            'GGBR4', 'KLBN11', 'SUZB3', 'FIBR3', 'ELET3', 'ELET6', 'CMIG4',
            'CPFE3', 'EGIE3', 'ENGI11', 'TAEE11', 'VIVT3', 'TIMP3', 'TIMS3',
            'RADL3', 'RAIA3', 'PCAR3', 'FLRY3', 'QUAL3', 'HAPV3', 'PLAN4',
            'GNDI3', 'ODPV3', 'NTCO3', 'LWSA3', 'CASH3', 'PETZ3', 'VVAR3',
            'SBSP3', 'SAPR11', 'CSAN3', 'UGPA3', 'SMTO3', 'YDUQ3', 'COGN3',
            'ARZZ3', 'SOMA3', 'GMAT3', 'PRIO3', 'RECV3', 'EVEN3', 'JHSF3',
            'BRML3', 'BRAP4', 'SLCE3', 'ALPA4', 'CMIN3', 'BRKM5', 'POMO4',
            'TOTS3', 'DXCO3', 'IRBR3', 'SULA11', 'PSSA3', 'CVCB3', 'HYPE3'
        ]
    
    def get_company_data(self, ticker: str) -> Optional[Dict]:
        """
        Obtém dados completos de uma empresa
        
        Args:
            ticker: Código da ação (ex: PETR4)
            
        Returns:
            Dicionário com dados da empresa ou None se falhar
        """
        try:
            return self.collector.collect_company_data(ticker)
        except Exception as e:
            logger.error(f"Erro ao coletar dados de {ticker}: {e}")
            return None
    
    def get_all_companies_data(self) -> List[Dict]:
        """
        Obtém dados de todas as empresas do Ibovespa
        
        Returns:
            Lista com dados de todas as empresas
        """
        logger.info("Iniciando coleta de dados do Ibovespa com brapi.dev")
        
        all_data = []
        successful_collections = 0
        failed_collections = 0
        
        for i, ticker in enumerate(self.ibovespa_companies, 1):
            logger.info(f"Coletando dados de {ticker} ({i}/{len(self.ibovespa_companies)})")
            
            try:
                company_data = self.get_company_data(ticker)
                
                if company_data:
                    all_data.append(company_data)
                    successful_collections += 1
                    logger.info(f"✓ {ticker}: {company_data.get('company_name', 'N/A')}")
                else:
                    failed_collections += 1
                    logger.warning(f"✗ {ticker}: Dados não disponíveis")
                    
            except Exception as e:
                failed_collections += 1
                logger.error(f"✗ {ticker}: Erro na coleta - {e}")
        
        logger.info(f"Coleta concluída: {successful_collections} sucessos, {failed_collections} falhas")
        return all_data
    
    def get_company_financial_data(self, ticker: str) -> Optional[Dict]:
        """
        Obtém dados financeiros específicos para cálculos EVA/EFV
        
        Args:
            ticker: Código da ação
            
        Returns:
            Dados financeiros estruturados
        """
        company_data = self.get_company_data(ticker)
        
        if not company_data:
            return None
        
        # Estrutura os dados para compatibilidade com o sistema existente
        financial_data = {
            'ticker': ticker,
            'company_name': company_data.get('company_name'),
            
            # Dados de mercado
            'market_cap': company_data.get('market_cap'),
            'stock_price': company_data.get('stock_price'),
            'shares_outstanding': company_data.get('shares_outstanding'),
            
            # Dados do balanço
            'total_assets': company_data.get('total_assets'),
            'total_liabilities': company_data.get('total_liabilities'),
            'stockholder_equity': company_data.get('stockholder_equity'),
            'total_debt': company_data.get('total_debt'),
            'cash_and_equivalents': company_data.get('cash_and_equivalents'),
            
            # Dados da DRE
            'total_revenue': company_data.get('total_revenue'),
            'net_income': company_data.get('net_income'),
            'operating_income': company_data.get('operating_income'),
            'ebitda': company_data.get('ebitda'),
            'interest_expense': company_data.get('interest_expense'),
            
            # Dados do fluxo de caixa
            'operating_cash_flow': company_data.get('operating_cash_flow'),
            'free_cash_flow': company_data.get('free_cash_flow'),
            'capital_expenditures': company_data.get('capital_expenditures'),
            
            # Múltiplos
            'pe_ratio': company_data.get('pe_ratio'),
            'price_to_book': company_data.get('price_to_book'),
            'earnings_per_share': company_data.get('earnings_per_share'),
            'book_value_per_share': company_data.get('book_value_per_share'),
            
            # Metadados
            'currency': company_data.get('currency', 'BRL'),
            'collected_at': company_data.get('collected_at'),
            'data_source': 'brapi.dev'
        }
        
        return financial_data
    
    def get_historical_prices(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """
        Obtém dados históricos de preços
        
        Args:
            ticker: Código da ação
            period: Período dos dados
            
        Returns:
            DataFrame com dados históricos
        """
        try:
            return self.collector.get_historical_data(ticker, period)
        except Exception as e:
            logger.error(f"Erro ao obter dados históricos de {ticker}: {e}")
            return pd.DataFrame()
    
    def validate_data_quality(self, data: List[Dict]) -> Dict:
        """
        Valida a qualidade dos dados coletados
        
        Args:
            data: Lista de dados das empresas
            
        Returns:
            Relatório de qualidade dos dados
        """
        if not data:
            return {
                'total_companies': 0,
                'valid_companies': 0,
                'data_quality_score': 0,
                'missing_fields': [],
                'recommendations': ['Nenhum dado coletado']
            }
        
        total_companies = len(data)
        valid_companies = 0
        missing_fields = {}
        
        # Campos essenciais para análise EVA/EFV
        essential_fields = [
            'market_cap', 'stock_price', 'total_assets', 'stockholder_equity',
            'net_income', 'total_revenue', 'total_debt'
        ]
        
        for company in data:
            is_valid = True
            
            for field in essential_fields:
                if not company.get(field):
                    is_valid = False
                    if field not in missing_fields:
                        missing_fields[field] = 0
                    missing_fields[field] += 1
            
            if is_valid:
                valid_companies += 1
        
        data_quality_score = (valid_companies / total_companies) * 100 if total_companies > 0 else 0
        
        # Recomendações baseadas na qualidade
        recommendations = []
        if data_quality_score < 70:
            recommendations.append("Qualidade dos dados baixa. Considere usar fonte alternativa.")
        if missing_fields:
            most_missing = max(missing_fields, key=missing_fields.get)
            recommendations.append(f"Campo '{most_missing}' ausente em {missing_fields[most_missing]} empresas.")
        if data_quality_score >= 90:
            recommendations.append("Excelente qualidade dos dados. Análise confiável.")
        
        return {
            'total_companies': total_companies,
            'valid_companies': valid_companies,
            'data_quality_score': round(data_quality_score, 2),
            'missing_fields': missing_fields,
            'recommendations': recommendations
        }
    
    def get_ibovespa_companies_list(self) -> List[str]:
        """
        Retorna a lista de empresas do Ibovespa
        
        Returns:
            Lista de tickers
        """
        return self.ibovespa_companies.copy()

# Função de conveniência para compatibilidade com o código existente
def get_ibovespa_data() -> List[Dict]:
    """
    Função de conveniência para obter dados do Ibovespa
    Mantém compatibilidade com o código existente
    
    Returns:
        Lista com dados das empresas do Ibovespa
    """
    collector = IbovespaDataImproved()
    return collector.get_all_companies_data()

def get_company_data(ticker: str) -> Optional[Dict]:
    """
    Função de conveniência para obter dados de uma empresa específica
    
    Args:
        ticker: Código da ação
        
    Returns:
        Dados da empresa
    """
    collector = IbovespaDataImproved()
    return collector.get_company_financial_data(ticker)

# Exemplo de uso
if __name__ == "__main__":
    # Teste do novo coletor
    collector = IbovespaDataImproved()
    
    # Testa uma empresa específica
    print("Testando coleta de dados da PETR4...")
    petr4_data = collector.get_company_financial_data("PETR4")
    
    if petr4_data:
        print(f"✓ Empresa: {petr4_data['company_name']}")
        print(f"✓ Market Cap: R$ {petr4_data.get('market_cap', 'N/A'):,}")
        print(f"✓ Preço: R$ {petr4_data.get('stock_price', 'N/A')}")
        print(f"✓ Patrimônio Líquido: R$ {petr4_data.get('stockholder_equity', 'N/A'):,}")
    else:
        print("✗ Falha na coleta de dados")
    
    # Testa coleta de algumas empresas
    print("\nTestando coleta de múltiplas empresas...")
    test_companies = ['VALE3', 'ITUB4', 'BBDC4']
    
    for ticker in test_companies:
        data = collector.get_company_financial_data(ticker)
        if data:
            print(f"✓ {ticker}: {data['company_name']}")
        else:
            print(f"✗ {ticker}: Falha na coleta")
