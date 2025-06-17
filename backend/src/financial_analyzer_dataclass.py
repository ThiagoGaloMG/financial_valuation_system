# backend/src/financial_analyzer_dataclass.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class CompanyFinancialData:
    """
    Estrutura para armazenar todos os dados financeiros e de mercado de uma empresa.
    Isolada neste arquivo para evitar problemas de importação circular.
    """
    ticker: str
    company_name: str
    market_cap: float
    stock_price: float
    shares_outstanding: float
    revenue: float
    ebit: float
    net_income: float
    depreciation_amortization: float
    capex: float
    total_assets: float
    total_debt: float
    equity: float
    current_assets: float
    current_liabilities: float
    cash: float
    accounts_receivable: float
    inventory: float
    accounts_payable: float
    property_plant_equipment: Optional[float] = None
    sector: Optional[str] = None
