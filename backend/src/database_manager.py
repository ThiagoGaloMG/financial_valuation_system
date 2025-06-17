# backend/src/database_manager.py
# Módulo centralizado para todas as interações com o banco de dados Supabase (PostgreSQL).

import psycopg2
import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Configura um logger específico para este módulo.
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gerencia a conexão e as operações com o banco de dados PostgreSQL (Supabase).
    Esta classe abstrai toda a lógica de banco de dados, atuando como uma camada
    de persistência para a aplicação.
    """
    def __init__(self):
        """
        Inicializa o gerenciador de banco de dados.
        Constrói a string de conexão a partir das variáveis de ambiente,
        que serão injetadas pelo Render no ambiente de produção.
        """
        try:
            # Constrói a string de conexão a partir de variáveis de ambiente individuais.
            # Este é o método recomendado para plataformas como o Render.
            self.conn_string = (
                f"dbname='{os.environ.get('DB_NAME')}' "
                f"user='{os.environ.get('DB_USER')}' "
                f"host='{os.environ.get('DB_HOST')}' "
                f"password='{os.environ.get('DB_PASSWORD')}' "
                f"port='{os.environ.get('DB_PORT', 5432)}'" # Usa 5432 como porta padrão
            )
            # Verifica se alguma variável essencial está faltando
            if not all([os.environ.get('DB_NAME'), os.environ.get('DB_USER'), os.environ.get('DB_HOST'), os.environ.get('DB_PASSWORD')]):
                raise TypeError("Uma ou mais variáveis de ambiente do banco de dados não estão definidas.")

        except TypeError as e:
            logger.critical(f"CREDENCIAIS DO BANCO DE DADOS INCOMPLETAS: {e}. O DatabaseManager não poderá se conectar.")
            self.conn_string = None

    def _get_connection(self):
        """
        Estabelece e retorna uma nova conexão com o banco de dados.
        Lança um erro se a string de conexão não estiver disponível.
        """
        if not self.conn_string:
            raise ConnectionError("A string de conexão com o banco de dados não está disponível. Verifique as variáveis de ambiente.")
        
        # O timeout evita que a aplicação fique presa indefinidamente ao tentar conectar.
        return psycopg2.connect(self.conn_string, connect_timeout=10)

    def get_latest_analysis_report(self, max_age_hours: int = 12) -> Optional[Dict[str, Any]]:
        """
        Busca o relatório de análise mais recente. Atua como um cache.
        Retorna o relatório (como um dicionário Python) se ele for recente, 
        caso contrário retorna None.

        Args:
            max_age_hours: O tempo máximo em horas que um relatório é considerado válido.
        """
        # SQL para buscar o dado JSON do relatório mais recente dentro do tempo limite.
        sql = "SELECT report_data FROM public.analysis_reports WHERE created_at > %s ORDER BY created_at DESC LIMIT 1;"
        
        if not self.conn_string: 
            logger.warning("Não foi possível buscar relatório pois a conexão com o DB não está configurada.")
            return None
        
        try:
            # A utilização do 'with' garante que a conexão será fechada automaticamente.
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Calcula o tempo limite para o cache (agora - max_age_hours)
                    time_threshold = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
                    
                    cur.execute(sql, (time_threshold,))
                    latest_report = cur.fetchone()

                    if latest_report:
                        logger.info(f"Relatório recente (com menos de {max_age_hours}h) encontrado no cache do DB.")
                        # O resultado da query já é um dicionário Python pois psycopg2 lida com JSONB.
                        return latest_report[0]
                    else:
                        logger.info("Nenhum relatório recente encontrado no cache do DB. Uma nova análise será necessária.")
                        return None
        except psycopg2.Error as e:
            logger.error(f"Erro de banco de dados ao buscar relatório: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar relatório no DB: {e}", exc_info=True)
            
        return None

    def save_analysis_report(self, report_data: Dict[str, Any]) -> None:
        """
        Salva um novo relatório de análise (um grande objeto JSON) no banco de dados.

        Args:
            report_data: Um dicionário Python contendo todos os dados do relatório a serem salvos.
        """
        sql = "INSERT INTO public.analysis_reports (report_data) VALUES (%s);"
        
        if not self.conn_string:
            logger.error("Não foi possível salvar relatório pois a conexão com o DB não está configurada.")
            return

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # O psycopg2 converte o dicionário Python para o formato JSONB do PostgreSQL
                    # ao passar o dicionário como um parâmetro para json.dumps.
                    cur.execute(sql, (json.dumps(report_data),))
                # O 'with' statement faz o commit da transação aqui, se não houver erros.
                logger.info("Novo relatório de análise salvo com sucesso no banco de dados.")
        except psycopg2.Error as e:
            logger.error(f"Erro de banco de dados ao salvar relatório: {e}", exc_info=True)
            # O 'with' statement fará o rollback da transação em caso de erro.
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar relatório no DB: {e}", exc_info=True)
