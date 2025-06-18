# backend/src/db/database.py

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

# Carrega variáveis de ambiente de um .env (somente em desenvolvimento local)
load_dotenv()

def get_connection():
    """
    Retorna uma conexão psycopg2 ao banco Postgres (Supabase).
    Espera as variáveis de ambiente:
      - DB_HOST
      - DB_PORT
      - DB_USER
      - DB_PASSWORD
      - DB_NAME
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DBNAME"),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar ao banco: {e}")

def get_or_create_company(ticker: str, company_name: str, sector: str = None) -> str:
    """
    Insere ou atualiza uma empresa na tabela `companies`, retornando o UUID (id).
    Usa UPSERT em ticker único:
      - Se não existe, insere.
      - Se existe, atualiza company_name e sector (se fornecido) e last_updated.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        query = """
            INSERT INTO public.companies (ticker, company_name, sector)
            VALUES (%s, %s, %s)
            ON CONFLICT (ticker) DO UPDATE
              SET company_name = EXCLUDED.company_name,
                  sector = COALESCE(EXCLUDED.sector, public.companies.sector),
                  last_updated = now()
            RETURNING id;
        """
        cur.execute(query, (ticker, company_name, sector))
        row = cur.fetchone()
        conn.commit()
        if row:
            return row[0]
        else:
            raise RuntimeError("Falha ao obter ID após upsert em companies")
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Erro em get_or_create_company: {e}")
    finally:
        cur.close()
        conn.close()

def insert_or_update_financial_metrics(
    company_id: str,
    analysis_date: datetime,
    metrics: dict,
    raw_data: dict = None
) -> str:
    """
    Insere ou atualiza métricas financeiras na tabela `financial_metrics`, retornando o UUID (id).
    Usa UPSERT em (company_id, analysis_date) conforme constraint unique_company_date_metric.
    Campos esperados em `metrics` (NUMERIC):
      - market_cap
      - stock_price
      - wacc_percentual
      - eva_abs
      - eva_percentual
      - efv_abs
      - efv_percentual
      - riqueza_atual
      - riqueza_futura
      - upside_percentual
      - combined_score
    `raw_data` será armazenado em JSONB (pode ser None).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        raw_json = json.dumps(raw_data) if raw_data is not None else None
        query = """
            INSERT INTO public.financial_metrics
              (company_id, analysis_date, market_cap, stock_price, wacc_percentual, eva_abs, eva_percentual,
               efv_abs, efv_percentual, riqueza_atual, riqueza_futura, upside_percentual, combined_score, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, analysis_date) DO UPDATE
              SET market_cap = EXCLUDED.market_cap,
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
        """
        values = (
            company_id,
            analysis_date,
            metrics.get("market_cap"),
            metrics.get("stock_price"),
            metrics.get("wacc_percentual"),
            metrics.get("eva_abs"),
            metrics.get("eva_percentual"),
            metrics.get("efv_abs"),
            metrics.get("efv_percentual"),
            metrics.get("riqueza_atual"),
            metrics.get("riqueza_futura"),
            metrics.get("upside_percentual"),
            metrics.get("combined_score"),
            raw_json
        )
        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        if row:
            return row[0]
        else:
            raise RuntimeError("Falha ao obter ID após upsert em financial_metrics")
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Erro em insert_or_update_financial_metrics: {e}")
    finally:
        cur.close()
        conn.close()

def insert_analysis_report(report: dict):
    """
    Insere um relatório agregado na tabela `analysis_reports`.
    Usa campos do dict `report`:
      - report_name (text) [obrigatório]
      - report_summary JSONB (ou summary_statistics)
      - full_ranking_data JSONB (ou full_report_data)
      - report_type TEXT
      - execution_time_seconds NUMERIC
    A coluna report_date usa DEFAULT now().
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Extrair campos do report, com chaves alternativas se necessário
        report_name = report.get("report_name") or report.get("name") or "Análise"
        summary = report.get("report_summary") or report.get("summary_statistics") or {}
        full = report.get("full_ranking_data") or report.get("full_report_data") or {}
        report_type = report.get("report_type")
        if not report_type:
            # Inferir tipo: se num_companies fornecido no report
            if report.get("num_companies") is not None:
                report_type = "quick"
            else:
                report_type = "full"
        execution_time = report.get("execution_time_seconds") or report.get("execution_time") or 0

        query = """
            INSERT INTO public.analysis_reports
              (report_name, report_summary, full_ranking_data, report_type, execution_time_seconds)
            VALUES (%s, %s, %s, %s, %s);
        """
        cur.execute(query, (
            report_name,
            json.dumps(summary),
            json.dumps(full),
            report_type,
            execution_time
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Erro em insert_analysis_report: {e}")
    finally:
        cur.close()
        conn.close()
