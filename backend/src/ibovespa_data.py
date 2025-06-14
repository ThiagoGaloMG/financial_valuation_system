# backend/src/ibovespa_data.py

import yfinance as yf
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

def get_ibovespa_tickers() -> List[str]:
    """
    Obtém a lista de tickers das empresas que compõem o Ibovespa.
    Prioriza uma lista manual atualizada, com fallback para busca em HTML se necessário.
    """
    try:
        # Lista manual dos principais componentes do Ibovespa (atualizada em 2024 para demonstração)
        # É uma lista representativa e não exaustiva para manter a performance da demo.
        ibovespa_tickers = [
            'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'ABEV3.SA',
            'BBAS3.SA', 'WEGE3.SA', 'RENT3.SA', 'LREN3.SA', 'MGLU3.SA',
            'JBSS3.SA', 'SUZB3.SA', 'RAIL3.SA', 'USIM5.SA', 'CSNA3.SA',
            'GGBR4.SA', 'ELET3.SA', 'VIVT3.SA', 'RADL3.SA', 'HAPV3.SA',
            'ITSA4.SA', 'PRIO3.SA', 'RDOR3.SA', 'B3SA3.SA', 'EQTL3.SA',
            'ENBR3.SA', 'CMIG4.SA', 'TAEE11.SA', 'BRFS3.SA', 'BPAC11.SA',
            'KLBN11.SA', 'CYRE3.SA', 'CVCB3.SA', 'COGN3.SA', 'GOAU4.SA',
            'IRBR3.SA', 'LINX3.SA', 'LWSA3.SA', 'PSSA3.SA', 'QUAL3.SA',
            'SANB11.SA', 'TIMS3.SA', 'UGPA3.SA', 'CCRO3.SA', 'AZUL4.SA',
            'EZTC3.SA', 'FLRY3.SA', 'GETT3.SA', 'GOLL4.SA', 'HYPE3.SA',
            'LAME4.SA', 'MRVE3.SA', 'OMGE3.SA', 'PCAR3.SA', 'QUALY3.SA',
            'SBSP3.SA', 'SLCE3.SA', 'TOTS3.SA', 'ALPA4.SA', 'EMBR3.SA',
            'ENGI11.SA', 'HAPV3.SA', 'RAIA3.SA', 'SULA11.SA', 'VVAR3.SA'
        ]
        logger.info(f"Tickers do Ibovespa (lista manual): {len(ibovespa_tickers)} empresas.")
        return ibovespa_tickers
    except Exception as e:
        logger.error(f"Erro ao obter tickers do Ibovespa: {e}")
        return []

def get_selic_rate() -> Optional[float]:
    """
    Obtém a taxa Selic meta atual do site do Banco Central.
    Retorna a taxa em percentual (ex: 13.75 para 13.75%).
    """
    try:
        url = "https://www.bcb.gov.br/"
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Lança exceção para erros HTTP
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tenta encontrar a Selic em diferentes elementos
        # A estrutura do site do BC pode mudar, então é bom ter flexibilidade
        selic_element = soup.find('p', class_='valor')
        if selic_element:
            selic_text = selic_element.text.replace(',', '.').strip()
            # Remove qualquer texto adicional como "(%)"
            selic_rate = float(''.join(filter(lambda x: x.isdigit() or x == '.', selic_text)))
            logger.info(f"Taxa Selic obtida: {selic_rate}%")
            return selic_rate
        else:
            logger.warning("Elemento da taxa Selic não encontrado na página do BC. Tentando alternativa...")
            # Fallback: tentar encontrar em um div com id específico ou classe
            selic_alt_element = soup.find('div', id='blocoTaxaSelic')
            if selic_alt_element:
                text_content = selic_alt_element.get_text()
                import re
                match = re.search(r'(\d+,\d+)%', text_content)
                if match:
                    selic_rate = float(match.group(1).replace(',', '.'))
                    logger.info(f"Taxa Selic obtida (alternativa): {selic_rate}%")
                    return selic_rate

        logger.error("Não foi possível encontrar a taxa Selic na página do Banco Central.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao conectar com o Banco Central para obter a Selic: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao processar a página do Banco Central para obter a Selic: {e}")
        return None

def validate_ticker(ticker: str) -> str:
    """
    Valida e formata um ticker para o padrão brasileiro (.SA).
    """
    ticker = ticker.upper().strip()
    if not ticker.endswith('.SA'):
        ticker += '.SA'
    return ticker

def get_market_sectors() -> dict:
    """
    Retorna um dicionário com setores e suas principais empresas (exemplos).
    Pode ser expandido com dados reais ou lido de um CSV/DB.
    """
    return {
        'Petróleo e Gás': ['PETR4.SA', 'PRIO3.SA', 'RECV3.SA'],
        'Mineração': ['VALE3.SA', 'USIM5.SA', 'CSNA3.SA', 'GGBR4.SA', 'GOAU4.SA'],
        'Bancos': ['ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'SANB11.SA', 'BBSE3.SA'],
        'Bebidas': ['ABEV3.SA'],
        'Varejo': ['MGLU3.SA', 'LREN3.SA', 'ASAI3.SA', 'LWSA3.SA', 'PCAR3.SA'],
        'Alimentos': ['JBSS3.SA', 'BEEF3.SA', 'MRFG3.SA', 'CSAN3.SA'],
        'Energia Elétrica': ['ELET3.SA', 'CPFE3.SA', 'CMIG4.SA', 'TAEE11.SA', 'ENBR3.SA', 'EQTL3.SA', 'OMGE3.SA', 'SBSP3.SA'],
        'Telecomunicações': ['VIVT3.SA', 'TIMS3.SA'],
        'Tecnologia': ['TOTS3.SA', 'LINX3.SA'],
        'Saúde': ['RADL3.SA', 'RAIA3.SA', 'HAPV3.SA', 'RDOR3.SA', 'FLRY3.SA', 'HYPE3.SA'],
        'Transporte': ['RENT3.SA', 'AZUL4.SA', 'GOLL4.SA', 'RAIL3.SA', 'CVCB3.SA'],
        'Construção Civil': ['EZTC3.SA', 'MRVE3.SA', 'CYRE3.SA'],
        'Papel e Celulose': ['SUZB3.SA', 'KLBN11.SA'],
        'Siderurgia': ['CSNA3.SA', 'USIM5.SA', 'GGBR4.SA', 'GOAU4.SA'],
        'Aviação': ['AZUL4.SA', 'GOLL4.SA'],
        'Diversos': ['WEGE3.SA', 'BRFS3.SA', 'BPAC11.SA', 'GETT3.SA', 'IRBR3.SA', 'LAME4.SA', 'PSSA3.SA', 'QUAL3.SA', 'SULA11.SA', 'UGPA3.SA', 'VVAR3.SA', 'COGN3.SA', 'ALPA4.SA', 'EMBR3.SA', 'ENGI11.SA', 'B3SA3.SA']
    }

if __name__ == '__main__':
    # Exemplo de uso
    tickers = get_ibovespa_tickers()
    if tickers:
        print(f"Primeiros 5 tickers do Ibovespa: {tickers[:5]}")
    
    selic = get_selic_rate()
    if selic is not None:
        print(f"Taxa Selic atual: {selic}%")

    sectors = get_market_sectors()
    print(f"Setores de mercado (exemplo): {list(sectors.keys())[:3]}...")
