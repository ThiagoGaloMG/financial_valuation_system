# backend/src/ibovespa_data.py

import pandas as pd
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL da B3 para a composição da carteira do Ibovespa.
# NOTA: Esta URL pode mudar. Se parar de funcionar, será necessário encontrar a nova URL da carteira teórica.
URL_IBOVESPA = 'https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/eyJsYW5ndWFnZSI6InB0LWJyIiwicGFnZU51bWJlciI6MSwicGFnZVNpemUiOjEyMCwiaW5kZXgiOiJJQk9WIiwic2VnbWVudCI6IjEifQ=='

def get_ibovespa_tickers() -> List[str]:
    """
    Busca a lista de tickers que compõem o índice Ibovespa diretamente da B3.
    Retorna uma lista de tickers formatados para o yfinance (ex: 'PETR4.SA').
    """
    logger.info("Buscando tickers do Ibovespa na B3...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(URL_IBOVESPA, headers=headers)
        response.raise_for_status()  # Lança um erro para status HTTP ruins (4xx ou 5xx)
        data = response.json()
        
        tickers = [f"{item['cod']}.SA" for item in data.get('results', [])]
        
        if not tickers:
            logger.warning("A lista de tickers do Ibovespa retornou vazia. Verifique a URL da B3.")
            return []
            
        logger.info(f"Encontrados {len(tickers)} tickers no Ibovespa.")
        return tickers
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de rede ao buscar tickers do Ibovespa: {e}")
    except Exception as e:
        logger.error(f"Erro ao processar dados dos tickers do Ibovespa: {e}")
    
    # Retorna uma lista vazia em caso de falha
    return []

def get_selic_rate() -> float:
    """
    Busca a taxa Selic atual do webservice do Banco Central do Brasil.
    Retorna a taxa Selic anualizada como um float (ex: 10.5).
    """
    logger.info("Buscando a taxa Selic no Banco Central...")
    # URL do webservice de séries temporais do BCB para a Selic (código 1178)
    url_selic = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados/ultimos/1?formato=json'
    
    try:
        response = requests.get(url_selic)
        response.raise_for_status()
        data = response.json()
        
        if data and isinstance(data, list) and 'valor' in data[0]:
            # A taxa vem como percentual ao dia. Para anualizar: (1 + taxa_diaria)^252 - 1
            # O BCB já fornece a taxa anualizada na meta (código 432), mas a série 1178 é a DI.
            # A série 1178 (CDI) é mais próxima do custo de oportunidade sem risco.
            # O valor já vem como % a.a., mas a base é 252 dias. Não precisa de conversão complexa.
            selic_rate = float(data[0]['valor'])
            logger.info(f"Taxa Selic (CDI) encontrada: {selic_rate:.2f}% a.a.")
            return selic_rate
        else:
            logger.warning("Formato de dados da Selic inesperado.")
            return 10.5 # Retorna um valor padrão razoável se a busca falhar
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de rede ao buscar taxa Selic: {e}")
    except Exception as e:
        logger.error(f"Erro ao processar dados da Selic: {e}")
        
    return 10.5 # Retorna um valor padrão razoável em caso de falha

def get_market_sectors() -> Dict[str, List[str]]:
    """
    Busca os setores de atuação das empresas do Ibovespa.
    Esta função usa scraping e pode ser instável. Em um projeto real,
    seria melhor usar uma API paga ou um banco de dados próprio.
    """
    logger.info("Buscando setores das empresas do Ibovespa (pode levar um tempo)...")
    # Usa uma fonte confiável como a B3 ou um portal financeiro
    url = "https://www.fundamentus.com.br/resultado.php"
    headers = {'User-agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', {'id': 'resultado'})
        if not table:
            logger.warning("Tabela de resultados não encontrada no Fundamentus.")
            return {}
            
        rows = table.find_all('tr')[1:] # Ignorar cabeçalho
        
        sectors = {}
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 1:
                ticker_raw = cols[0].text.strip()
                sector_text = cols[-1].text.strip() # A última coluna geralmente é o setor
                
                # Agrupar setores similares (simplificação)
                if 'finan' in sector_text.lower() or 'segur' in sector_text.lower():
                    sector_group = 'Financeiro e Seguros'
                elif 'energ' in sector_text.lower() or 'petr' in sector_text.lower():
                    sector_group = 'Energia e Petróleo'
                elif 'varej' in sector_text.lower() or 'comerc' in sector_text.lower():
                    sector_group = 'Varejo e Comércio'
                elif 'saude' in sector_text.lower():
                    sector_group = 'Saúde'
                elif 'ind' in sector_text.lower():
                    sector_group = 'Industrial'
                else:
                    sector_group = 'Outros' # Agrupa os demais
                
                if sector_group not in sectors:
                    sectors[sector_group] = []
                sectors[sector_group].append(f"{ticker_raw}.SA")

        logger.info("Setores das empresas coletados com sucesso.")
        return sectors
        
    except Exception as e:
        logger.error(f"Erro ao fazer scraping dos setores: {e}")
        return {}


if __name__ == '__main__':
    # Teste para as funções
    print("--- Testando get_ibovespa_tickers ---")
    tickers = get_ibovespa_tickers()
    if tickers:
        print(f"Primeiros 5 tickers: {tickers[:5]}")
    else:
        print("Não foi possível buscar os tickers.")

    print("\n--- Testando get_selic_rate ---")
    selic = get_selic_rate()
    if selic:
        print(f"Taxa Selic: {selic}%")
    else:
        print("Não foi possível buscar a taxa Selic.")
        
    print("\n--- Testando get_market_sectors ---")
    market_sectors = get_market_sectors()
    if market_sectors:
        for sector, companies in list(market_sectors.items())[:3]: # Mostra 3 setores para o demo
            print(f"Setor: {sector}, Empresas: {companies[:2]}") # Mostra 2 empresas por setor
    else:
        print("Não foi possível buscar os setores.")
