import { useState, useEffect, useRef } from 'react';
import { Button } from './components/ui/button.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card.jsx';
import { Input } from './components/ui/input.jsx';
import { Label } from './components/ui/label.jsx';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs.jsx';
import { Badge } from './components/ui/badge.jsx';
import { Alert, AlertDescription } from './components/ui/alert.jsx';
import { Loader2, Info, Zap, Activity } from 'lucide-react';
import Chart from 'chart.js/auto';
import './App.css';
import './index.css';

// Lê a URL base do backend a partir das variáveis de ambiente do Vite.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// Componente para a tabela de ranking (para não ser recriado a cada renderização)
const RankingTable = ({ data }) => {
    const [sortedData, setSortedData] = useState(data);
    const [sortConfig, setSortConfig] = useState({ key: 'combined_score', direction: 'desc' });

    useEffect(() => {
        let dataToSort = [...data];
        dataToSort.sort((a, b) => {
            const valA = a[sortConfig.key];
            const valB = b[sortConfig.key];
            if (valA === null || isNaN(valA)) return 1;
            if (valB === null || isNaN(valB)) return -1;
            if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
            if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });
        setSortedData(dataToSort);
    }, [data, sortConfig]);

    const requestSort = (key) => {
        let direction = 'desc';
        if (sortConfig.key === key && sortConfig.direction === 'desc') {
            direction = 'asc';
        }
        setSortConfig({ key, direction });
    };

    const getSortIndicator = (columnKey) => {
        if (sortConfig.key === columnKey) {
            return sortConfig.direction === 'desc' ? ' ▼' : ' ▲';
        }
        return '';
    };

    const formatCurrency = (value) => {
        if (value === null || isNaN(value)) return 'N/A';
        if (Math.abs(value) >= 1e9) return `R$ ${(value / 1e9).toFixed(2)}B`;
        if (Math.abs(value) >= 1e6) return `R$ ${(value / 1e6).toFixed(2)}M`;
        return `R$ ${value.toFixed(2)}`;
    };

    const formatPercentage = (value) => {
        if (value === null || isNaN(value)) return 'N/A';
        return `${value.toFixed(2)}%`;
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Ranking Completo das Empresas</CardTitle>
                <CardDescription>Ordene pela métrica desejada clicando nos cabeçalhos.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto rounded-lg border">
                    <table className="min-w-full divide-y">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="th-style text-center">Pos.</th>
                                <th className="th-style cursor-pointer" onClick={() => requestSort('ticker')}>Ticker{getSortIndicator('ticker')}</th>
                                <th className="th-style cursor-pointer" onClick={() => requestSort('company_name')}>Empresa{getSortIndicator('company_name')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('combined_score')}>Score{getSortIndicator('combined_score')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('eva_percentual')}>EVA (%){getSortIndicator('eva_percentual')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('efv_percentual')}>EFV (%){getSortIndicator('efv_percentual')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('upside_percentual')}>Upside (%){getSortIndicator('upside_percentual')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('market_cap')}>Market Cap{getSortIndicator('market_cap')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {sortedData.map((company, index) => (
                                <tr key={company.ticker} className="hover:bg-slate-50">
                                    <td className="td-style text-center text-slate-500">{index + 1}</td>
                                    <td className="td-style font-medium text-slate-900">{company.ticker}</td>
                                    <td className="td-style text-slate-800">{company.company_name}</td>
                                    <td className="td-style text-right font-semibold text-blue-600">{company.combined_score?.toFixed(2) || 'N/A'}</td>
                                    <td className={`td-style text-right ${company.eva_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>{formatPercentage(company.eva_percentual)}</td>
                                    <td className={`td-style text-right ${company.efv_percentual > 0 ? 'text-blue-600' : 'text-red-600'}`}>{formatPercentage(company.efv_percentual)}</td>
                                    <td className={`td-style text-right ${company.upside_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>{formatPercentage(company.upside_percentual)}</td>
                                    <td className="td-style text-right text-slate-600">{formatCurrency(company.market_cap)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
};


function App() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [companyData, setCompanyData] = useState(null);
    const [fullAnalysisReport, setFullAnalysisReport] = useState(null);
    const [tickerInput, setTickerInput] = useState('');
    const [activeTab, setActiveTab] = useState('dashboard');
    const chartInstances = useRef({});

    // Funções de formatação
    const formatCurrency = (value) => {
        if (value === null || isNaN(value)) return 'N/A';
        if (Math.abs(value) >= 1e9) return `R$ ${(value / 1e9).toFixed(2)}B`;
        if (Math.abs(value) >= 1e6) return `R$ ${(value / 1e6).toFixed(2)}M`;
        return `R$ ${value.toFixed(2)}`;
    };

    const formatPercentage = (value) => {
        if (value === null || isNaN(value)) return 'N/A';
        return `${value.toFixed(2)}%`;
    };
    
    const formatDate = (isoString) => {
        if (!isoString) return 'N/A';
        return new Date(isoString).toLocaleDateString('pt-BR');
    };

    // Função centralizada para buscar dados da API
    const fetchAnalysis = async (endpoint, options = {}) => {
        setLoading(true);
        setError('');
        try {
            // CORREÇÃO: Usando crases (template literals) para montar a URL corretamente.
            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
            if (!response.ok) {
                // Tenta extrair uma mensagem de erro do backend, senão usa o status http
                const errorText = await response.text();
                let errorMessage;
                try {
                    const errorJson = JSON.parse(errorText);
                    errorMessage = errorJson.message || `Erro no servidor: ${response.status}`;
                } catch {
                    errorMessage = errorText || `Erro no servidor: ${response.status}`;
                }
                throw new Error(errorMessage);
            }
            return await response.json();
        } catch (err) {
            console.error("Erro ao buscar dados:", err);
            setError(err.message);
            return null;
        } finally {
            setLoading(false);
        }
    };

    const handleRunAnalysis = async (num_companies = null) => {
        const report = await fetchAnalysis('/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ num_companies }),
        });
        if (report) {
            setFullAnalysisReport(report);
            setCompanyData(null);
            setActiveTab('dashboard');
        }
    };

    const handleSearchCompany = async (e) => {
        e.preventDefault();
        if (!tickerInput) {
            setError('Por favor, insira um ticker para buscar.');
            return;
        }
        const data = await fetchAnalysis(`/company/${tickerInput.toUpperCase().trim()}`);
        if (data) {
            setCompanyData(data);
            setFullAnalysisReport(null);
            setActiveTab('company-details');
        }
    };

    // Efeito para gerenciar os gráficos
    useEffect(() => {
        const destroyChart = (chartId) => {
            if (chartInstances.current[chartId]) {
                chartInstances.current[chartId].destroy();
                delete chartInstances.current[chartId];
            }
        };

        if (activeTab === 'dashboard' && fullAnalysisReport?.full_report_data) {
            destroyChart('scatterChart');
            const ctx = document.getElementById('scatterChart');
            if(ctx) {
                chartInstances.current.scatterChart = new Chart(ctx, {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: 'Empresas',
                            data: fullAnalysisReport.full_report_data.map(c => ({ x: c.eva_percentual, y: c.efv_percentual, label: c.ticker })),
                            backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.raw.label}: EVA ${c.raw.x?.toFixed(2)}%, EFV ${c.raw.y?.toFixed(2)}%` } } },
                        scales: { x: { title: { display: true, text: 'EVA (%)' } }, y: { title: { display: true, text: 'EFV (%)' } } }
                    }
                });
            }
        }
        
        // Limpeza dos gráficos ao desmontar o componente
        return () => { Object.values(chartInstances.current).forEach(chart => chart.destroy()); };
    }, [activeTab, fullAnalysisReport]);

    return (
        <div className="min-h-screen bg-slate-100 text-slate-800 antialiased">
            <div className="container mx-auto p-4 md:p-8 max-w-7xl">
                <header className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-slate-900">Sistema de Análise Financeira</h1>
                    <p className="text-slate-600 mt-2">Valuation de Empresas do Ibovespa (EVA & EFV)</p>
                </header>

                <main>
                    {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
                    {loading && (
                        <div className="flex justify-center items-center my-6">
                            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                            <span className="ml-4 text-lg text-blue-700">Analisando... Este processo pode levar alguns minutos.</span>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                        <Card>
                            <CardHeader><CardTitle>Análise de Mercado</CardTitle><CardDescription>Analise as principais empresas ou o Ibovespa completo.</CardDescription></CardHeader>
                            <CardContent className="flex flex-col gap-3">
                                <Button onClick={() => handleRunAnalysis(15)} disabled={loading}><Zap className="mr-2 h-4 w-4" />Análise Rápida (15 Empresas)</Button>
                                <Button onClick={() => handleRunAnalysis(null)} disabled={loading} variant="secondary"><Activity className="mr-2 h-4 w-4" />Análise Completa (Ibovespa)</Button>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader><CardTitle>Análise por Empresa</CardTitle><CardDescription>Obtenha uma análise detalhada de uma empresa específica.</CardDescription></CardHeader>
                            <CardContent>
                                <form onSubmit={handleSearchCompany} className="flex flex-col gap-3">
                                    <Label htmlFor="ticker">Ticker da Empresa</Label>
                                    <div className="flex gap-2">
                                        <Input id="ticker" type="text" placeholder="Ex: PETR4.SA" value={tickerInput} onChange={(e) => setTickerInput(e.target.value)} />
                                        <Button type="submit" disabled={loading}><Info className="mr-2 h-4 w-4" />Buscar</Button>
                                    </div>
                                </form>
                            </CardContent>
                        </Card>
                    </div>

                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
                            <TabsTrigger value="full-ranking">Ranking Completo</TabsTrigger>
                            <TabsTrigger value="company-details" disabled={!companyData}>Empresa Detalhada</TabsTrigger>
                        </TabsList>

                        <TabsContent value="dashboard" className="mt-6">
                            {fullAnalysisReport ? (
                                <div className="space-y-6">
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                        <Card><CardHeader><CardTitle className="text-sm font-medium">Empresas Analisadas</CardTitle><CardContent><p className="text-2xl font-bold">{fullAnalysisReport.total_companies_analyzed}</p></CardContent></CardHeader></Card>
                                        <Card><CardHeader><CardTitle className="text-sm font-medium">Criando Valor (EVA > 0)</CardTitle><CardContent><p className="text-2xl font-bold text-green-600">{fullAnalysisReport.summary_statistics.positive_eva_count}</p></CardContent></CardHeader></Card>
                                        <Card><CardHeader><CardTitle className="text-sm font-medium">Potencial Futuro (EFV > 0)</CardTitle><CardContent><p className="text-2xl font-bold text-blue-600">{fullAnalysisReport.summary_statistics.positive_efv_count}</p></CardContent></CardHeader></Card>
                                        <Card><CardHeader><CardTitle className="text-sm font-medium">Data da Análise</CardTitle><CardContent><p className="text-2xl font-bold">{formatDate(fullAnalysisReport.timestamp)}</p></CardContent></CardHeader></Card>
                                    </div>
                                    <Card>
                                        <CardHeader><CardTitle>Dispersão EVA vs. EFV</CardTitle><CardDescription>Identifique empresas com forte valor atual e alto potencial futuro.</CardDescription></CardHeader>
                                        <CardContent><div className="chart-container"><canvas id="scatterChart"></canvas></div></CardContent>
                                    </Card>
                                </div>
                            ) : (<Alert className="mt-4"><Info className="h-4 w-4" /><AlertDescription>Execute uma análise para ver o Dashboard.</AlertDescription></Alert>)}
                        </TabsContent>

                        <TabsContent value="full-ranking" className="mt-6">
                            {fullAnalysisReport ? (<RankingTable data={fullAnalysisReport.full_report_data} />) : (<Alert><Info className="h-4 w-4" /><AlertDescription>Execute uma análise para ver o Ranking Completo.</AlertDescription></Alert>)}
                        </TabsContent>

                        <TabsContent value="company-details" className="mt-6">
                            {companyData ? (
                                <Card>
                                    <CardHeader><CardTitle>{companyData.company_name} ({companyData.ticker})</CardTitle><CardDescription>Análise Detalhada de Valuation</CardDescription></CardHeader>
                                    <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                        <div className="p-4 rounded-lg bg-slate-100"><h3 className="text-sm font-medium text-slate-500">Market Cap</h3><p className="text-xl font-bold">{formatCurrency(companyData.metrics.market_cap)}</p></div>
                                        <div className="p-4 rounded-lg bg-slate-100"><h3 className="text-sm font-medium text-slate-500">Preço da Ação</h3><p className="text-xl font-bold">{formatCurrency(companyData.metrics.stock_price)}</p></div>
                                        <div className="p-4 rounded-lg bg-slate-100"><h3 className="text-sm font-medium text-slate-500">WACC</h3><p className="text-xl font-bold">{formatPercentage(companyData.metrics.wacc_percentual)}</p></div>
                                        <div className="p-4 rounded-lg bg-slate-100"><h3 className="text-sm font-medium text-slate-500">EVA (%)</h3><p className={`text-xl font-bold ${companyData.metrics.eva_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>{formatPercentage(companyData.metrics.eva_percentual)}</p></div>
                                        <div className="p-4 rounded-lg bg-slate-100"><h3 className="text-sm font-medium text-slate-500">EFV (%)</h3><p className={`text-xl font-bold ${companyData.metrics.efv_percentual > 0 ? 'text-blue-600' : 'text-red-600'}`}>{formatPercentage(companyData.metrics.efv_percentual)}</p></div>
                                        <div className="p-4 rounded-lg bg-slate-100"><h3 className="text-sm font-medium text-slate-500">Upside Potencial</h3><p className={`text-xl font-bold ${companyData.metrics.upside_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>{formatPercentage(companyData.metrics.upside_percentual)}</p></div>
                                    </CardContent>
                                </Card>
                            ) : (<Alert><Info className="h-4 w-4" /><AlertDescription>Nenhuma empresa selecionada. Use a caixa de busca acima.</AlertDescription></Alert>)}
                        </TabsContent>
                    </Tabs>
                </main>
            </div>
        </div>
    );
}

export default App;
