# backend/src/ibovespa_data.py

import requests
import logging
from typing import List
from functools import lru_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurar logging para monitoramento
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# URL da API da B3 para a composição da carteira do Ibovespa
URL_IBOVESPA = (
    'https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/'
    'GetPortfolioDay/eyJsYW5ndWFnZSI6InB0LWJyIiwicGFnZU51bWJlciI6MSwicGFnZVNpemUiOjEyMCwiaW5kZXgiOiJJQk9WIiwic2VnbWVudCI6IjEifQ=='
)

# =====================================================================================
# LISTA DE FALLBACK (SEGURANÇA) - ATUALIZADA COM A LISTA COMPLETA FORNECIDA
# Se a busca na B3 falhar (comum em servidores de nuvem), usaremos esta lista
# para garantir que a aplicação sempre tenha tickers para analisar.
# =====================================================================================
FALLBACK_IBOVESPA_TICKERS = [
    "ALOS3.SA", "ABEV3.SA", "ASAI3.SA", "AURE3.SA", "AZUL4.SA", "B3SA3.SA",
    "BBSE3.SA", "BBDC3.SA", "BBDC4.SA", "BRAP4.SA", "BBAS3.SA", "BRKM5.SA",
    "BRFS3.SA", "BPAC11.SA", "CXSE3.SA", "CMIG4.SA", "COGN3.SA", "CPLE6.SA",
    "CSAN3.SA", "CPFE3.SA", "CMIN3.SA", "CVCB3.SA", "CYRE3.SA", "DIRR3.SA",
    "ELET3.SA", "ELET6.SA", "EMBR3.SA", "ENGI11.SA", "ENEV3.SA", "EGIE3.SA",
    "EQTL3.SA", "FLRY3.SA", "GGBR4.SA", "GOAU4.SA", "NTCO3.SA", "HAPV3.SA",
    "HYPE3.SA", "IGTI11.SA", "IRBR3.SA", "ITSA4.SA", "ITUB4.SA", "KLBN11.SA",
    "RENT3.SA", "LREN3.SA", "MGLU3.SA", "POMO4.SA", "MRFG3.SA", "BEEF3.SA",
    "MRVE3.SA", "MULT3.SA", "PCAR3.SA", "PETR3.SA", "PETR4.SA",
    "RECV3.SA", "PRIO3.SA", "PETZ3.SA", "PSSA3.SA", "RADL3.SA", "RAIZ4.SA",
    "RDOR3.SA", "RAIL3.SA", "SBSP3.SA", "SANB11.SA", "STBP3.SA", "SMTO3.SA",
    "CSNA3.SA", "SLCE3.SA", "SMFT3.SA", "SUZB3.SA", "TAEE11.SA", "VIVT3.SA",
    "TIMS3.SA", "TOTS3.SA", "UGPA3.SA", "USIM5.SA", "VALE3.SA", "VAMO3.SA",
    "VBBR3.SA", "VIVA3.SA", "WEGE3.SA", "YDUQ3.SA"
]

# Configura uma sessão de requests com retry para robustez
def _create_session_with_retries(total_retries: int = 3, backoff_factor: float = 0.3) -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

@lru_cache(maxsize=1)
def get_ibovespa_tickers() -> List[str]:
    """
    Busca a lista de tickers do Ibovespa. Tenta buscar da B3, mas usa uma
    lista de fallback completa em caso de falha para garantir a robustez da aplicação.
    O resultado é cacheado para evitar múltiplas requisições.
    """
    logger.info("Tentando buscar tickers do Ibovespa na B3...")
    session = _create_session_with_retries()
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
    }
    try:
        response = session.get(URL_IBOVESPA, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        tickers = [f"{item['cod']}.SA" for item in data.get('results', []) if item.get('cod')]
        if tickers:
            logger.info(f"Sucesso! Encontrados {len(tickers)} tickers na B3.")
            return tickers
        else:
            logger.warning("A busca na B3 não retornou tickers. Usando a lista de fallback.")
            return FALLBACK_IBOVESPA_TICKERS
    except Exception as e:
        logger.error(f"Falha ao buscar tickers da B3: {e}. Usando a lista de fallback.")
        return FALLBACK_IBOVESPA_TICKERS

@lru_cache(maxsize=1)
def get_selic_rate() -> float:
    """
    Busca a taxa Selic atual do webservice do Banco Central do Brasil.
    Retorna um valor padrão em caso de falha. Resultado cacheado para evitar múltiplas chamadas.
    """
    logger.info("Buscando a taxa Selic no Banco Central...")
    session = _create_session_with_retries()
    url_selic = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados/ultimos/1?formato=json'
    try:
        response = session.get(url_selic, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list) and data[0].get('valor') is not None:
            selic_rate = float(data[0]['valor'])
            logger.info(f"Taxa Selic encontrada: {selic_rate:.2f}% a.a.")
            return selic_rate
    except Exception as e:
        logger.error(f"Falha ao buscar taxa Selic: {e}. Usando valor padrão.")
    # Retorna um valor padrão razoável em caso de falha
    return 10.5
