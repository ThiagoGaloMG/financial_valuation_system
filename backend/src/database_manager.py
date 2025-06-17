# backend/src/database_manager.py

import psycopg2
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from financial_analyzer_dataclass import CompanyFinancialData  # certifique-se de importar do módulo correto

logger = logging.getLogger(__name__)

class SupabaseDB:
    def __init__(self):
        """
        Inicializa a conexão com Supabase/Postgres.
        A string de conexão é obtida da variável de ambiente DATABASE_URL.
        Opcionalmente, pode-se usar pool de conexões aqui.
        """
        self.conn_string = os.environ.get("DATABASE_URL")
        if not self.conn_string:
            logger.error("DATABASE_URL não configurada no ambiente. Conexão ao DB falhará.")
            # Poderíamos lançar um erro aqui para falhar cedo:
            # raise RuntimeError("DATABASE_URL não configurada")
        # Exemplo de pool (opcional):
        # from psycopg2.pool import SimpleConnectionPool
        # try:
        #     self.pool = SimpleConnectionPool(minconn=1, maxconn=10, dsn=self.conn_string)
        # except Exception as e:
        #     logger.error(f"Erro ao criar pool de conexões: {e}")
        #     self.pool = None

    def _get_connection(self):
        """
        Estabelece e retorna uma conexão com o banco de dados.
        Pode-se adicionar parâmetros como connect_timeout.
        Se usar pool, retorna conexão do pool.
        """
        if not self.conn_string:
            raise RuntimeError("DATABASE_URL não configurada")
        try:
            # Exemplo com timeout de 10s:
            conn = psycopg2.connect(self.conn_string, connect_timeout=10)
            return conn
            # Se usar pool:
            # if self.pool:
            #     return self.pool.getconn()
            # else:
            #     return psycopg2.connect(self.conn_string, connect_timeout=10)
        except Exception as e:
            logger.error(f"Erro ao conectar ao Supabase: {e}")
            raise

    def _close_connection(self, conn):
        """
        Fecha a conexão ou devolve ao pool.
        """
        try:
            # if hasattr(self, 'pool') and self.pool:
            #     self.pool.putconn(conn)
            # else:
            conn.close()
        except Exception as e:
            logger.warning(f"Erro ao fechar conexão: {e}")

    def save_analysis_report(self, report_data: Dict[str, Any]) -> Optional[str]:
        """
        Salva os dados de um relatório de análise completo no banco de dados.
        Retorna o ID (UUID string) inserido, ou None em caso de falha.
        Campos esperados em report_data:
         - report_name (str)
         - report_type (str)
         - execution_time_seconds (numérico)
         - summary_statistics (dict)
         - full_report_data (list/dict)
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Extrai dados do report_data para a tabela analysis_reports
                report_name = report_data.get('report_name', 'Análise Não Especificada')
                report_type = report_data.get('report_type', 'unknown')
                execution_time_seconds = report_data.get('execution_time_seconds')

                # Assegura que o JSONB seja um string JSON
                summary_obj = report_data.get('summary_statistics', {})
                full_ranking_obj = report_data.get('full_report_data', [])

                report_summary_json = json.dumps(summary_obj)
                full_ranking_data_json = json.dumps(full_ranking_obj)

                cur.execute(
                    """
                    INSERT INTO public.analysis_reports (
                        report_name, report_summary, full_ranking_data, report_type, execution_time_seconds
                    ) VALUES (%s, %s::jsonb, %s::jsonb, %s, %s)
                    RETURNING id;
                    """,
                    (report_name, report_summary_json, full_ranking_data_json, report_type, execution_time_seconds)
                )
                row = cur.fetchone()
                conn.commit()
                if row:
                    report_id = row[0]
                    logger.info(f"Relatório de análise '{report_name}' salvo com ID: {report_id}")
                    return str(report_id)
                else:
                    logger.error("Nenhum ID retornado ao salvar relatório de análise.")
                    return None
        except Exception:
            if conn:
                conn.rollback()
            logger.exception("Erro ao salvar relatório no Supabase")
            return None
        finally:
            if conn:
                self._close_connection(conn)

    def save_company_metrics(
        self,
        company_data_obj: CompanyFinancialData,
        metrics_data_dict: Dict[str, Any],
        analysis_date: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Salva as métricas calculadas para uma única empresa.
        Retorna ID do registro em financial_metrics (UUID string) ou None.
        Parâmetros:
         - company_data_obj: instância de CompanyFinancialData, com atributos ticker, company_name, sector, etc.
         - metrics_data_dict: dicionário com chaves: market_cap, stock_price, wacc_percentual, eva_abs, eva_percentual,
           efv_abs, efv_percentual, riqueza_atual, riqueza_futura, upside_percentual, combined_score, raw_data (dict opcional).
         - analysis_date: datetime para persistir (padrão: agora).
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # 1. Inserir ou atualizar na tabela companies (para garantir que a empresa existe)
                cur.execute(
                    """
                    INSERT INTO public.companies (ticker, company_name, sector, last_updated)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (ticker) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        sector = EXCLUDED.sector,
                        last_updated = now()
                    RETURNING id;
                    """,
                    (company_data_obj.ticker, company_data_obj.company_name, getattr(company_data_obj, 'sector', None))
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("Falha ao obter ID da tabela companies após upsert")
                company_id = row[0]

                # 2. Inserir ou atualizar métricas financeiras na tabela financial_metrics
                # analysis_date: se não passado, usa agora()
                dt = analysis_date or datetime.now()
                # Serializar raw_data
                raw_data = metrics_data_dict.get('raw_data', {})
                raw_data_json = json.dumps(raw_data) if raw_data is not None else None

                cur.execute(
                    """
                    INSERT INTO public.financial_metrics (
                        company_id, analysis_date, market_cap, stock_price,
                        wacc_percentual, eva_abs, eva_percentual, efv_abs, efv_percentual,
                        riqueza_atual, riqueza_futura, upside_percentual, combined_score, raw_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (company_id, analysis_date) DO UPDATE SET
                        market_cap = EXCLUDED.market_cap,
                        stock_price = EXCLUDED.stock_price,
                        wacc_percentual = EXCLUDED.wacc_percentual,
                        eva_abs = EXCLUDED.eva_abs,
                        eva_percentual = EXCLUDED.eva_percentual,
                        efv_abs = EXCLUDED.efv_abs,
                        efv_percentual = EXCLUDED.efv_percentual,
                        riqueza_atual = EXCLUDED.riqueza_atual,
                        riqueza_futura = EXCLUDED.riqueza_futura,
                        upside_percentual = EXCLUDED.upside_percentual,
                        combined_score = EXCLUDED.combined_score,
                        raw_data = EXCLUDED.raw_data
                    RETURNING id;
                    """,
                    (
                        company_id,
                        dt,
                        metrics_data_dict.get('market_cap'),
                        metrics_data_dict.get('stock_price'),
                        metrics_data_dict.get('wacc_percentual'),
                        metrics_data_dict.get('eva_abs'),
                        metrics_data_dict.get('eva_percentual'),
                        metrics_data_dict.get('efv_abs'),
                        metrics_data_dict.get('efv_percentual'),
                        metrics_data_dict.get('riqueza_atual'),
                        metrics_data_dict.get('riqueza_futura'),
                        metrics_data_dict.get('upside_percentual'),
                        metrics_data_dict.get('combined_score'),
                        raw_data_json
                    )
                )
                row2 = cur.fetchone()
                conn.commit()
                if row2:
                    metric_id = row2[0]
                    logger.info(f"Métricas para {company_data_obj.ticker} salvas/atualizadas com ID: {metric_id}")
                    return str(metric_id)
                else:
                    logger.warning("Nenhum ID retornado ao inserir métricas financeiras.")
                    return None
        except Exception:
            if conn:
                conn.rollback()
            logger.exception(f"Erro ao salvar métricas da empresa {company_data_obj.ticker} no Supabase")
            return None
        finally:
            if conn:
                self._close_connection(conn)

    def get_latest_full_analysis_report(self) -> Optional[Dict[str, Any]]:
        """
        Busca o relatório de análise completa mais recente do banco de dados.
        Retorna dict com chaves:
         - status, timestamp, total_companies_analyzed, summary_statistics, full_report_data, report_name, report_type, execution_time_seconds
        Ou None se não houver ou em caso de erro.
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT report_summary, full_ranking_data, report_date, execution_time_seconds, report_name, report_type
                    FROM public.analysis_reports
                    ORDER BY report_date DESC
                    LIMIT 1;
                    """
                )
                result = cur.fetchone()
                if not result:
                    return None

                summary_json, ranking_json, report_date, exec_time, report_name, report_type = result
                # Se for dict já, json.loads não é necessário; mas mantemos compatibilidade
                summary = json.loads(summary_json) if isinstance(summary_json, str) else summary_json
                ranking = json.loads(ranking_json) if isinstance(ranking_json, str) else ranking_json

                return {
                    "status": "success",
                    "timestamp": report_date.isoformat() if hasattr(report_date, 'isoformat') else str(report_date),
                    "total_companies_analyzed": summary.get('total_companies_analyzed', 0),
                    "summary_statistics": summary,
                    "full_report_data": ranking,
                    "report_name": report_name,
                    "report_type": report_type,
                    "execution_time_seconds": float(exec_time) if exec_time is not None else None
                }
        except Exception:
            logger.exception("Erro ao buscar relatório completo mais recente do Supabase")
            return None
        finally:
            if conn:
                self._close_connection(conn)

    def get_company_latest_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Busca as métricas mais recentes de uma empresa específica.
        Retorna dict com estrutura similar ao endpoint /company/<ticker>.
        Ou None se não encontrado ou em caso de erro.
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        fm.market_cap, fm.stock_price, fm.wacc_percentual, fm.eva_abs, fm.eva_percentual,
                        fm.efv_abs, fm.efv_percentual, fm.riqueza_atual, fm.riqueza_futura,
                        fm.upside_percentual, fm.combined_score, fm.raw_data, c.company_name, c.ticker
                    FROM public.financial_metrics fm
                    JOIN public.companies c ON fm.company_id = c.id
                    WHERE c.ticker = %s
                    ORDER BY fm.analysis_date DESC
                    LIMIT 1;
                    """,
                    (ticker,)
                )
                result = cur.fetchone()
                if not result:
                    return None

                (
                    market_cap, stock_price, wacc_pct, eva_abs, eva_pct, efv_abs, efv_pct,
                    riqueza_atual, riqueza_futura, upside_pct, combined_score, raw_data_json,
                    company_name, ticker_from_db
                ) = result

                raw_data = None
                if raw_data_json is not None:
                    try:
                        raw_data = json.loads(raw_data_json) if isinstance(raw_data_json, str) else raw_data_json
                    except Exception:
                        logger.warning(f"Falha ao desserializar raw_data JSON para {ticker}")

                return {
                    "status": "success",
                    "ticker": ticker_from_db,
                    "company_name": company_name,
                    "metrics": {
                        "market_cap": float(market_cap) if market_cap is not None else None,
                        "stock_price": float(stock_price) if stock_price is not None else None,
                        "wacc_percentual": float(wacc_pct) if wacc_pct is not None else None,
                        "eva_abs": float(eva_abs) if eva_abs is not None else None,
                        "eva_percentual": float(eva_pct) if eva_pct is not None else None,
                        "efv_abs": float(efv_abs) if efv_abs is not None else None,
                        "efv_percentual": float(efv_pct) if efv_pct is not None else None,
                        "riqueza_atual": float(riqueza_atual) if riqueza_atual is not None else None,
                        "riqueza_futura": float(riqueza_futura) if riqueza_futura is not None else None,
                        "upside_percentual": float(upside_pct) if upside_pct is not None else None,
                        "combined_score": float(combined_score) if combined_score is not None else None,
                        "raw_data": raw_data
                    }
                }
        except Exception:
            logger.exception(f"Erro ao buscar métricas da empresa {ticker} no Supabase")
            return None
        finally:
            if conn:
                self._close_connection(conn)
