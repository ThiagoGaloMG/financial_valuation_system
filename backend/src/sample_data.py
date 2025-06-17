# backend/src/sample_data.py
# Este arquivo contém dados de exemplo para garantir que a aplicação
# funcione mesmo se as fontes externas (yfinance) estiverem bloqueando requisições.

# --- CORREÇÃO PRINCIPAL ---
# A importação agora vem do arquivo dedicado, quebrando a dependência circular.
from financial_analyzer_dataclass import CompanyFinancialData

# Dados de exemplo para algumas das principais empresas do Ibovespa.
# Os valores são representativos e servem para demonstração.
sample_financial_data = {
    "PETR4.SA": CompanyFinancialData(
        ticker='PETR4.SA', company_name='Petróleo Brasileiro S.A. - Petrobras', market_cap=502e9, stock_price=38.50,
        shares_outstanding=13.04e9, revenue=450e9, ebit=200e9, net_income=100e9,
        depreciation_amortization=80e9, capex=60e9, total_assets=1.3e12, total_debt=400e9,
        equity=500e9, current_assets=300e9, current_liabilities=180e9, cash=70e9,
        accounts_receivable=90e9, inventory=50e9, accounts_payable=80e9,
        property_plant_equipment=800e9, sector='Energia'
    ),
    "VALE3.SA": CompanyFinancialData(
        ticker='VALE3.SA', company_name='Vale S.A.', market_cap=280e9, stock_price=61.50,
        shares_outstanding=4.55e9, revenue=220e9, ebit=70e9, net_income=40e9,
        depreciation_amortization=25e9, capex=22e9, total_assets=650e9, total_debt=70e9,
        equity=280e9, current_assets=150e9, current_liabilities=100e9, cash=40e9,
        accounts_receivable=50e9, inventory=30e9, accounts_payable=40e9,
        property_plant_equipment=450e9, sector='Mineração'
    ),
    "ITUB4.SA": CompanyFinancialData(
        ticker='ITUB4.SA', company_name='Itaú Unibanco Holding S.A.', market_cap=300e9, stock_price=32.50,
        shares_outstanding=9.23e9, revenue=200e9, ebit=75e9, net_income=40e9,
        depreciation_amortization=10e9, capex=8e9, total_assets=2.8e12, total_debt=2.2e12,
        equity=220e9, current_assets=1.8e12, current_liabilities=1.7e12, cash=200e9,
        accounts_receivable=0, inventory=0, accounts_payable=0,
        property_plant_equipment=60e9, sector='Financeiro'
    ),
    "BBDC4.SA": CompanyFinancialData(
        ticker='BBDC4.SA', company_name='Banco Bradesco S.A.', market_cap=135e9, stock_price=12.80,
        shares_outstanding=10.5e9, revenue=160e9, ebit=30e9, net_income=15e9, depreciation_amortization=8e9,
        capex=5e9, total_assets=2.0e12, total_debt=1.6e12, equity=150e9, current_assets=1.4e12,
        current_liabilities=1.3e12, cash=100e9, accounts_receivable=0, inventory=0, accounts_payable=0,
        property_plant_equipment=40e9, sector='Financeiro'
    ),
    "WEGE3.SA": CompanyFinancialData(
        ticker='WEGE3.SA', company_name='WEG S.A.', market_cap=165e9, stock_price=39.30,
        shares_outstanding=4.2e9, revenue=32e9, ebit=6e9, net_income=5e9, depreciation_amortization=1e9,
        capex=1.5e9, total_assets=50e9, total_debt=10e9, equity=25e9, current_assets=30e9,
        current_liabilities=15e9, cash=5e9, accounts_receivable=8e9, inventory=10e9, accounts_payable=7e9,
        property_plant_equipment=15e9, sector='Industrial'
    )
}
