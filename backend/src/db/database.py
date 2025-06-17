# backend/src/db/database.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        return psycopg2.connect(
            dbname=os.getenv("dbname"),
            user=os.getenv("user"),
            password=os.getenv("password"),
            host=os.getenv("host"),
            port=os.getenv("port"),
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar ao banco de dados: {e}")

def insert_analysis_report(report):
    query = """
        INSERT INTO analysis_reports (report_name, report_summary, full_ranking_data, report_type, execution_time_seconds)
        VALUES (%s, %s, %s, %s, %s)
    """
    values = (
        report.get("report_name", "Análise Completa"),
        json.dumps(report.get("summary_statistics")),
        json.dumps(report.get("full_report_data")),
        report.get("report_type", "full"),
        report.get("execution_time_seconds", 0)
    )
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, values)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Erro ao inserir análise: {e}")
    finally:
        cur.close()
        conn.close()
