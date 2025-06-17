// frontend/src/App.jsx

import React, { useState, useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
import { Loader2, Info, Zap, Activity, ChevronUp, ChevronDown, Sparkles, BrainCircuit } from 'lucide-react';

// Importando seus componentes de UI. Certifique-se que os caminhos estão corretos.
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from './components/ui/alert';

// Importando estilos globais
import './App.css';
import './index.css';

// --- Funções Utilitárias ---
const formatCurrency = (value) => {
    if (value === null || typeof value === 'undefined' || isNaN(value)) return 'N/A';
    if (Math.abs(value) >= 1e9) return `R$ ${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6) return `R$ ${(value / 1e6).toFixed(2)}M`;
    return `R$ ${value.toFixed(2)}`;
};

const formatPercentage = (value) => {
    if (value === null || typeof value === 'undefined' || isNaN(value)) return 'N/A';
    return `${value.toFixed(2)}%`;
};

const getSemanticColor = (value) => {
    if (value === null || typeof value === 'undefined' || isNaN(value)) return 'text-slate-600';
    return value >= 0 ? 'text-green-600' : 'text-red-600';
};

// --- Componente Reutilizável para Gráficos ---
const ChartComponent = ({ chartId, type, data, options }) => {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (chartRef.current) {
            chartRef.current.destroy();
        }
        if (canvasRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            chartRef.current = new Chart(ctx, { type, data, options });
        }
        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, [type, data, options]);

    return <div className="chart-container"><canvas ref={canvasRef} id={chartId}></canvas></div>;
};


// --- Componentes de Views ---

const OverviewView = ({ report, navigateToDetails }) => {
    if (!report || !report.summary_statistics || !report.full_ranking_data) return null;

    const { summary_statistics, full_ranking_data } = report;
    const top5Companies = [...full_ranking_data].sort((a, b) => (b.metrics?.combined_score || 0) - (a.metrics?.combined_score || 0)).slice(0, 5);

    const chartData = {
        labels: top5Companies.map(c => c.ticker),
        datasets: [{
            label: 'Score Combinado',
            data: top5Companies.map(c => c.metrics?.combined_score),
            backgroundColor: 'rgba(59, 130, 246, 0.7)',
            borderColor: 'rgba(59, 130, 246, 1)',
            borderWidth: 1,
            barThickness: 25,
        }]
    };
    const chartOptions = { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } };
    
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card><CardHeader><CardTitle className="text-sm font-medium">Empresas Analisadas</CardTitle><CardContent><p className="text-2xl font-bold">{summary_statistics.total_companies_analyzed}</p></CardContent></CardHeader></Card>
                <Card><CardHeader><CardTitle className="text-sm font-medium">Criando Valor (EVA > 0)</CardTitle><CardContent><p className="text-2xl font-bold text-green-600">{summary_statistics.positive_eva_count}</p></CardContent></CardHeader></Card>
                <Card><CardHeader><CardTitle className="text-sm font-medium">Potencial Futuro (EFV > 0)</CardTitle><CardContent><p className="text-2xl font-bold text-blue-600">{summary_statistics.positive_efv_count}</p></CardContent></CardHeader></Card>
                <Card><CardHeader><CardTitle className="text-sm font-medium">Upside Médio</CardTitle><CardContent><p className={`text-2xl font-bold ${getSemanticColor(summary_statistics.average_upside)}`}>{formatPercentage(summary_statistics.average_upside)}</p></CardContent></CardHeader></Card>
            </div>
            <Card>
                <CardHeader>
                    <CardTitle>Top 5 Empresas por Score</CardTitle>
                    <CardDescription>As empresas com a melhor combinação de métricas de valor.</CardDescription>
                </CardHeader>
                <CardContent>
                    <ChartComponent chartId="top5Chart" type="bar" data={chartData} options={chartOptions} />
                </CardContent>
            </Card>
        </div>
    );
};

const RankingView = ({ data, navigateToDetails }) => {
    const [sortedData, setSortedData] = useState(data);
    const [sortConfig, setSortConfig] = useState({ key: 'combined_score', direction: 'desc' });

    useEffect(() => {
        let dataToSort = [...data];
        dataToSort.sort((a, b) => {
            const valA = a.metrics?.[sortConfig.key];
            const valB = b.metrics?.[sortConfig.key];
            if (valA === null || typeof valA === 'undefined') return 1;
            if (valB === null || typeof valB === 'undefined') return -1;
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
            return sortConfig.direction === 'desc' ? <ChevronDown className="inline h-4 w-4" /> : <ChevronUp className="inline h-4 w-4" />;
        }
        return null;
    };
    
    return (
        <Card>
            <CardHeader>
                <CardTitle>Ranking Completo do Ibovespa</CardTitle>
                <CardDescription>Clique nos cabeçalhos para ordenar as empresas por diferentes métricas de valor.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto rounded-lg border">
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="th-style text-center">#</th>
                                <th className="th-style cursor-pointer" onClick={() => requestSort('ticker')}>Ticker {getSortIndicator('ticker')}</th>
                                <th className="th-style cursor-pointer" onClick={() => requestSort('company_name')}>Empresa {getSortIndicator('company_name')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('combined_score')}>Score {getSortIndicator('combined_score')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('eva_percentual')}>EVA (%) {getSortIndicator('eva_percentual')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('upside_percentual')}>Upside (%) {getSortIndicator('upside_percentual')}</th>
                                <th className="th-style text-right cursor-pointer" onClick={() => requestSort('market_cap')}>Market Cap {getSortIndicator('market_cap')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 bg-white">
                            {sortedData.map((company, index) => (
                                <tr key={company.ticker} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigateToDetails(company.ticker)}>
                                    <td className="td-style text-center text-slate-500">{index + 1}</td>
                                    <td className="td-style font-semibold text-blue-600">{company.ticker}</td>
                                    <td className="td-style text-slate-800">{company.company_name}</td>
                                    <td className="td-style text-right font-semibold text-slate-900">{company.metrics?.combined_score?.toFixed(2) || 'N/A'}</td>
                                    <td className={`td-style text-right font-medium ${getSemanticColor(company.metrics?.eva_percentual)}`}>{formatPercentage(company.metrics?.eva_percentual)}</td>
                                    <td className={`td-style text-right font-medium ${getSemanticColor(company.metrics?.upside_percentual)}`}>{formatPercentage(company.metrics?.upside_percentual)}</td>
                                    <td className="td-style text-right text-slate-600">{formatCurrency(company.metrics?.market_cap)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
};

const DetailsView = ({ allData, ticker, setCurrentTicker }) => {
    const [aiAnalysis, setAiAnalysis] = useState('');
    const [isAiLoading, setIsAiLoading] = useState(false);
    const [aiError, setAiError] = useState('');

    const company = allData.find(c => c.ticker === ticker);

    const handleGenerateAiAnalysis = async () => {
        if (!company) return;
        setIsAiLoading(true);
        setAiError('');
        setAiAnalysis('');

        const { metrics, company_name, ticker } = company;
        const prompt = `Você é um analista financeiro. Crie uma análise qualitativa concisa para a empresa ${company_name} (${ticker}), baseando-se estritamente nos seguintes dados: Score: ${metrics.combined_score.toFixed(1)}/10, EVA: ${formatPercentage(metrics.eva_percentual)}, Upside: ${formatPercentage(metrics.upside_percentual)}, WACC: ${formatPercentage(metrics.wacc_percentual)}. Formate a resposta em Markdown com seções "Resumo", "Pontos Fortes", e "Pontos de Atenção".`;
        
        try {
            const payload = { contents: [{ role: "user", parts: [{ text: prompt }] }] };
            const apiKey = ""; // Injetado pelo ambiente de execução
            const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error(`API do Gemini retornou erro ${response.status}`);
            const result = await response.json();
            const text = result.candidates?.[0]?.content?.parts?.[0]?.text;
            if (text) {
                setAiAnalysis(text.replace(/\*\*(.*?)\*\*/g, '<h4>$1</h4>').replace(/\* (.*?)/g, '<li>$1</li>'));
            } else {
                throw new Error("Resposta da API de IA inválida.");
            }
        } catch (err) {
            setAiError(err.message);
        } finally {
            setIsAiLoading(false);
        }
    };
    
    if (!company) {
         return <Alert><Info className="h-4 w-4" /><AlertDescription>Selecione uma empresa no ranking para ver os detalhes.</AlertDescription></Alert>;
    }
    
    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <div className="flex justify-between items-start">
                        <div>
                            <CardTitle>{company.company_name}</CardTitle>
                            <CardDescription>{company.ticker}</CardDescription>
                        </div>
                         <select onChange={(e) => setCurrentTicker(e.target.value)} value={ticker} className="select-style">
                            {allData.map(c => <option key={c.ticker} value={c.ticker}>{c.ticker}</option>)}
                        </select>
                    </div>
                </CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4">
                     <div className="metric-card"><h3 className="metric-title">Market Cap</h3><p className="metric-value">{formatCurrency(company.metrics.market_cap)}</p></div>
                     <div className="metric-card"><h3 className="metric-title">Preço da Ação</h3><p className="metric-value">{formatCurrency(company.metrics.stock_price)}</p></div>
                     <div className="metric-card"><h3 className="metric-title">WACC</h3><p className="metric-value">{formatPercentage(company.metrics.wacc_percentual)}</p></div>
                     <div className="metric-card"><h3 className="metric-title">EVA (%)</h3><p className={`metric-value ${getSemanticColor(company.metrics.eva_percentual)}`}>{formatPercentage(company.metrics.eva_percentual)}</p></div>
                     <div className="metric-card"><h3 className="metric-title">Upside (%)</h3><p className={`metric-value ${getSemanticColor(company.metrics.upside_percentual)}`}>{formatPercentage(company.metrics.upside_percentual)}</p></div>
                     <div className="metric-card"><h3 className="metric-title">Score</h3><p className="metric-value text-blue-600">{company.metrics.combined_score?.toFixed(2)}</p></div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><BrainCircuit className="text-blue-600" /> Análise Qualitativa com IA</CardTitle>
                    <CardDescription>Clique no botão para gerar uma análise com base nos indicadores financeiros, usando a API do Gemini.</CardDescription>
                </CardHeader>
                 <CardContent>
                    <Button onClick={handleGenerateAiAnalysis} disabled={isAiLoading}>
                        {isAiLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                        Gerar Análise
                    </Button>
                    {aiError && <Alert variant="destructive" className="mt-4"><AlertDescription>{aiError}</AlertDescription></Alert>}
                    {aiAnalysis && <div className="mt-4 prose" dangerouslySetInnerHTML={{ __html: aiAnalysis }} />}
                </CardContent>
            </Card>
        </div>
    );
};


// --- Componente Principal da Aplicação ---

function App() {
    const [fullAnalysisReport, setFullAnalysisReport] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentView, setCurrentView] = useState('overview');
    const [currentTicker, setCurrentTicker] = useState(null);

    useEffect(() => {
        const fetchAllData = async () => {
            setIsLoading(true);
            setError(null);
            try {
                // A URL relativa funciona por causa do proxy no vite.config.js e da regra no render.yaml
                const response = await fetch('/api/v1/ranking/full');
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Erro na API: ${response.status} - ${errorText}`);
                }
                const data = await response.json();
                
                // O backend agora retorna o relatório completo
                if (!data || !data.full_ranking_data) {
                     throw new Error('A API retornou dados em um formato inesperado.');
                }
                
                setFullAnalysisReport(data);

                if (data.full_ranking_data.length > 0) {
                   const sorted = [...data.full_ranking_data].sort((a,b) => (b.metrics?.combined_score || 0) - (a.metrics?.combined_score || 0));
                   setCurrentTicker(sorted[0].ticker);
                }
            } catch (err) {
                setError(err.message);
                console.error("Falha ao buscar dados do backend:", err);
            } finally {
                setIsLoading(false);
            }
        };

        fetchAllData();
    }, []);

    const navigateToDetails = (ticker) => {
        setCurrentTicker(ticker);
        setCurrentView('details');
    }

    const renderContent = () => {
        if (isLoading) {
            return (
                <div className="flex flex-col items-center justify-center p-12 bg-white rounded-lg shadow-sm">
                    <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
                    <p className="mt-4 text-slate-600 font-medium">Buscando e analisando dados de mercado...</p>
                    <p className="text-sm text-slate-500">Na primeira execução do dia, isso pode levar alguns minutos.</p>
                </div>
            );
        }

        if (error) {
            return (
                <Alert variant="destructive" className="mt-4">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Erro de Conexão</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            );
        }

        if (!fullAnalysisReport) return null;

        switch (currentView) {
            case 'ranking':
                return <RankingView data={fullAnalysisReport.full_ranking_data} navigateToDetails={navigateToDetails} />;
            case 'details':
                 return <DetailsView allData={fullAnalysisReport.full_ranking_data} ticker={currentTicker} setCurrentTicker={setCurrentTicker} />;
            case 'overview':
            default:
                return <OverviewView report={fullAnalysisReport} navigateToDetails={navigateToDetails} />;
        }
    };
    
    return (
        <div className="min-h-screen bg-slate-50 text-slate-900">
            <div className="container mx-auto p-4 md:p-8 max-w-7xl">
                <header className="text-center mb-8">
                    <h1 className="text-4xl font-bold">Sistema de Análise Financeira</h1>
                    <p className="text-slate-600 mt-2">Valuation de Empresas do Ibovespa por EVA</p>
                </header>
                
                <Tabs value={currentView} onValueChange={setCurrentView} className="w-full">
                    <TabsList className="grid w-full grid-cols-3 mb-6">
                        <TabsTrigger value="overview">Visão Geral</TabsTrigger>
                        <TabsTrigger value="ranking">Ranking Completo</TabsTrigger>
                        <TabsTrigger value="details" disabled={!currentTicker}>Análise Detalhada</TabsTrigger>
                    </TabsList>
                    <main>{renderContent()}</main>
                </Tabs>

                <footer className="text-center mt-12 pt-6 border-t border-slate-200">
                    <p className="text-sm text-slate-500">Desenvolvido por Thiago Marques Lopes. UI/UX e Deploy por Gemini.</p>
                </footer>
            </div>
        </div>
    );
}

export default App;
