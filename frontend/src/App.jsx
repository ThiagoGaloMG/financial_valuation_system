// frontend/src/App.jsx - Versão Melhorada com Design Profissional

import React, { useState, useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
import { 
  Loader2, 
  Info, 
  Zap, 
  Activity, 
  ChevronUp, 
  ChevronDown, 
  Sparkles, 
  BrainCircuit,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  PieChart,
  Building2,
  AlertCircle
} from 'lucide-react';

// Importando componentes de UI
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from './components/ui/alert';

// Importando estilos
import './App.css';
import './index.css';

// --- Funções Utilitárias ---
const formatCurrency = (value) => {
    if (value === null || typeof value === 'undefined' || isNaN(value)) return 'N/A';
    if (Math.abs(value) >= 1e9) return `R$ ${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6) return `R$ ${(value / 1e6).toFixed(2)}M`;
    if (Math.abs(value) >= 1e3) return `R$ ${(value / 1e3).toFixed(2)}K`;
    return `R$ ${value.toFixed(2)}`;
};

const formatPercentage = (value) => {
    if (value === null || typeof value === 'undefined' || isNaN(value)) return 'N/A';
    return `${value.toFixed(2)}%`;
};

const getSemanticColor = (value) => {
    if (value === null || typeof value === 'undefined' || isNaN(value)) return 'text-slate-500';
    return value >= 0 ? 'text-emerald-600' : 'text-red-500';
};

const getSemanticIcon = (value) => {
    if (value === null || typeof value === 'undefined' || isNaN(value)) return null;
    return value >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />;
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

    return (
        <div className="chart-container h-64 w-full">
            <canvas ref={canvasRef} id={chartId}></canvas>
        </div>
    );
};

// --- Componente de Loading ---
const LoadingSpinner = () => (
    <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-700 mb-2">Analisando o Ibovespa</h3>
            <p className="text-slate-500">Coletando dados financeiros e calculando métricas...</p>
        </div>
    </div>
);

// --- Componente de Erro ---
const ErrorDisplay = ({ error, onRetry }) => (
    <div className="flex items-center justify-center min-h-[400px]">
        <Card className="max-w-md">
            <CardHeader>
                <div className="flex items-center space-x-2">
                    <AlertCircle className="h-5 w-5 text-red-500" />
                    <CardTitle className="text-red-700">Erro na Análise</CardTitle>
                </div>
            </CardHeader>
            <CardContent>
                <p className="text-slate-600 mb-4">{error}</p>
                <Button onClick={onRetry} className="w-full">
                    <Activity className="mr-2 h-4 w-4" />
                    Tentar Novamente
                </Button>
            </CardContent>
        </Card>
    </div>
);

// --- Componente de Métrica ---
const MetricCard = ({ title, value, icon: Icon, trend, subtitle, className = "" }) => (
    <Card className={`transition-all duration-200 hover:shadow-lg ${className}`}>
        <CardContent className="p-6">
            <div className="flex items-center justify-between">
                <div className="flex-1">
                    <p className="text-sm font-medium text-slate-600 mb-1">{title}</p>
                    <div className="flex items-center space-x-2">
                        <p className="text-2xl font-bold text-slate-900">{value}</p>
                        {trend !== null && trend !== undefined && (
                            <div className={`flex items-center ${getSemanticColor(trend)}`}>
                                {getSemanticIcon(trend)}
                            </div>
                        )}
                    </div>
                    {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
                </div>
                {Icon && (
                    <div className="p-3 bg-blue-50 rounded-lg">
                        <Icon className="h-6 w-6 text-blue-600" />
                    </div>
                )}
            </div>
        </CardContent>
    </Card>
);

// --- Componentes de Views ---
const OverviewView = ({ report, navigateToDetails }) => {
    if (!report || !report.summary_statistics || !report.full_ranking_data) return null;

    const { summary_statistics, full_ranking_data } = report;
    const top5Companies = [...full_ranking_data]
        .sort((a, b) => (b.metrics?.combined_score || 0) - (a.metrics?.combined_score || 0))
        .slice(0, 5);

    const chartData = {
        labels: top5Companies.map(c => c.ticker.replace('.SA', '')),
        datasets: [{
            label: 'Score Combinado',
            data: top5Companies.map(c => c.metrics?.combined_score || 0),
            backgroundColor: [
                '#3b82f6',
                '#60a5fa',
                '#93c5fd',
                '#bfdbfe',
                '#dbeafe'
            ],
            borderColor: '#1e40af',
            borderWidth: 1,
            borderRadius: 8,
        }]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#1e293b',
                titleColor: '#f8fafc',
                bodyColor: '#f8fafc',
                borderColor: '#334155',
                borderWidth: 1,
            }
        },
        scales: {
            x: {
                beginAtZero: true,
                grid: { color: '#e2e8f0' },
                ticks: { color: '#64748b' }
            },
            y: {
                grid: { display: false },
                ticks: { color: '#64748b' }
            }
        }
    };
    
    return (
        <div className="space-y-8">
            {/* Métricas Principais */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    title="Empresas Analisadas"
                    value={summary_statistics.total_companies_analyzed}
                    icon={Building2}
                    subtitle="Empresas do Ibovespa"
                />
                <MetricCard
                    title="Criando Valor (EVA > 0)"
                    value={summary_statistics.positive_eva_count}
                    icon={TrendingUp}
                    subtitle="Empresas com EVA positivo"
                    className="border-l-4 border-l-emerald-500"
                />
                <MetricCard
                    title="Potencial Futuro (EFV > 0)"
                    value={summary_statistics.positive_efv_count}
                    icon={Zap}
                    subtitle="Empresas com EFV positivo"
                    className="border-l-4 border-l-blue-500"
                />
                <MetricCard
                    title="Upside Médio"
                    value={formatPercentage(summary_statistics.average_upside)}
                    icon={BarChart3}
                    trend={summary_statistics.average_upside}
                    subtitle="Potencial de valorização"
                />
            </div>

            {/* Gráfico Top 5 */}
            <Card className="shadow-lg">
                <CardHeader className="pb-4">
                    <div className="flex items-center space-x-2">
                        <PieChart className="h-5 w-5 text-blue-600" />
                        <CardTitle className="text-xl">Top 5 Empresas por Score</CardTitle>
                    </div>
                    <CardDescription>
                        As empresas com a melhor combinação de métricas de valor econômico.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <ChartComponent 
                        chartId="top5Chart" 
                        type="bar" 
                        data={chartData} 
                        options={chartOptions} 
                    />
                </CardContent>
            </Card>

            {/* Insights Rápidos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200">
                    <CardHeader>
                        <CardTitle className="text-emerald-800 flex items-center">
                            <TrendingUp className="mr-2 h-5 w-5" />
                            Criadores de Valor
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-emerald-700">
                            <span className="font-bold text-2xl">{summary_statistics.positive_eva_count}</span> empresas 
                            estão criando valor econômico (EVA positivo), representando{' '}
                            <span className="font-semibold">
                                {((summary_statistics.positive_eva_count / summary_statistics.total_companies_analyzed) * 100).toFixed(1)}%
                            </span> do Ibovespa.
                        </p>
                    </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
                    <CardHeader>
                        <CardTitle className="text-blue-800 flex items-center">
                            <Zap className="mr-2 h-5 w-5" />
                            Potencial Futuro
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-blue-700">
                            <span className="font-bold text-2xl">{summary_statistics.positive_efv_count}</span> empresas 
                            apresentam potencial de valor futuro (EFV positivo), indicando oportunidades de crescimento.
                        </p>
                    </CardContent>
                </Card>
            </div>
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
            return sortConfig.direction === 'desc' 
                ? <ChevronDown className="inline h-4 w-4 text-blue-600" /> 
                : <ChevronUp className="inline h-4 w-4 text-blue-600" />;
        }
        return <ChevronUp className="inline h-4 w-4 text-slate-300" />;
    };

    const getRankBadge = (index) => {
        if (index === 0) return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">🥇 1º</span>;
        if (index === 1) return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">🥈 2º</span>;
        if (index === 2) return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">🥉 3º</span>;
        return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">{index + 1}º</span>;
    };
    
    return (
        <Card className="shadow-lg">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-xl flex items-center">
                            <BarChart3 className="mr-2 h-5 w-5 text-blue-600" />
                            Ranking Completo do Ibovespa
                        </CardTitle>
                        <CardDescription className="mt-1">
                            Clique nos cabeçalhos para ordenar as empresas por diferentes métricas de valor.
                        </CardDescription>
                    </div>
                    <div className="text-sm text-slate-500">
                        {sortedData.length} empresas analisadas
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-slate-50 border-b border-slate-200">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                                    Posição
                                </th>
                                <th 
                                    className="px-6 py-4 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => requestSort('ticker')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Ticker</span>
                                        {getSortIndicator('ticker')}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 text-left text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => requestSort('company_name')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Empresa</span>
                                        {getSortIndicator('company_name')}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 text-right text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => requestSort('combined_score')}
                                >
                                    <div className="flex items-center justify-end space-x-1">
                                        <span>Score</span>
                                        {getSortIndicator('combined_score')}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 text-right text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => requestSort('eva_percentual')}
                                >
                                    <div className="flex items-center justify-end space-x-1">
                                        <span>EVA (%)</span>
                                        {getSortIndicator('eva_percentual')}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 text-right text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => requestSort('upside_percentual')}
                                >
                                    <div className="flex items-center justify-end space-x-1">
                                        <span>Upside (%)</span>
                                        {getSortIndicator('upside_percentual')}
                                    </div>
                                </th>
                                <th 
                                    className="px-6 py-4 text-right text-xs font-medium text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 transition-colors"
                                    onClick={() => requestSort('market_cap')}
                                >
                                    <div className="flex items-center justify-end space-x-1">
                                        <span>Market Cap</span>
                                        {getSortIndicator('market_cap')}
                                    </div>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-200">
                            {sortedData.map((company, index) => (
                                <tr 
                                    key={company.ticker} 
                                    className="hover:bg-slate-50 cursor-pointer transition-colors duration-150"
                                    onClick={() => navigateToDetails(company.ticker)}
                                >
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {getRankBadge(index)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="font-semibold text-blue-600 hover:text-blue-800">
                                            {company.ticker.replace('.SA', '')}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm font-medium text-slate-900 max-w-xs truncate">
                                            {company.company_name}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <div className="text-sm font-bold text-slate-900">
                                            {company.metrics?.combined_score?.toFixed(2) || 'N/A'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <div className={`text-sm font-medium flex items-center justify-end space-x-1 ${getSemanticColor(company.metrics?.eva_percentual)}`}>
                                            <span>{formatPercentage(company.metrics?.eva_percentual)}</span>
                                            {getSemanticIcon(company.metrics?.eva_percentual)}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <div className={`text-sm font-medium flex items-center justify-end space-x-1 ${getSemanticColor(company.metrics?.upside_percentual)}`}>
                                            <span>{formatPercentage(company.metrics?.upside_percentual)}</span>
                                            {getSemanticIcon(company.metrics?.upside_percentual)}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <div className="text-sm text-slate-600">
                                            {formatCurrency(company.metrics?.market_cap)}
                                        </div>
                                    </td>
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
        const prompt = `Você é um analista financeiro sênior. Crie uma análise qualitativa concisa para a empresa ${company_name} (${ticker}), baseando-se estritamente nos seguintes dados: Score: ${metrics.combined_score?.toFixed(1) || 'N/A'}/10, EVA: ${formatPercentage(metrics.eva_percentual)}, Upside: ${formatPercentage(metrics.upside_percentual)}, WACC: ${formatPercentage(metrics.wacc_percentual)}. Formate a resposta em Markdown com seções "## Resumo Executivo", "## Pontos Fortes", e "## Pontos de Atenção". Seja objetivo e profissional.`;
        
        try {
            const payload = { contents: [{ role: "user", parts: [{ text: prompt }] }] };
            const apiKey = ""; // Será injetado pelo ambiente
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
                setAiAnalysis(text);
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
         return (
            <Alert className="border-blue-200 bg-blue-50">
                <Info className="h-4 w-4 text-blue-600" />
                <AlertDescription className="text-blue-800">
                    Selecione uma empresa no ranking para ver os detalhes da análise financeira.
                </AlertDescription>
            </Alert>
         );
    }
    
    return (
        <div className="space-y-8">
            {/* Header da Empresa */}
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
                <CardHeader>
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
                        <div className="flex items-center space-x-4">
                            <div className="p-3 bg-blue-100 rounded-lg">
                                <Building2 className="h-8 w-8 text-blue-600" />
                            </div>
                            <div>
                                <CardTitle className="text-2xl text-blue-900">{company.company_name}</CardTitle>
                                <CardDescription className="text-blue-700 font-medium">
                                    {company.ticker.replace('.SA', '')} • Ibovespa
                                </CardDescription>
                            </div>
                        </div>
                        <div className="flex items-center space-x-4">
                            <select 
                                onChange={(e) => setCurrentTicker(e.target.value)} 
                                value={ticker} 
                                className="px-4 py-2 border border-blue-300 rounded-lg bg-white text-blue-900 font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                                {allData.map(c => (
                                    <option key={c.ticker} value={c.ticker}>
                                        {c.ticker.replace('.SA', '')} - {c.company_name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </CardHeader>
            </Card>

            {/* Métricas Principais */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <MetricCard
                    title="Market Cap"
                    value={formatCurrency(company.metrics.market_cap)}
                    icon={DollarSign}
                    subtitle="Valor de mercado"
                />
                <MetricCard
                    title="Preço da Ação"
                    value={formatCurrency(company.metrics.stock_price)}
                    icon={TrendingUp}
                    subtitle="Cotação atual"
                />
                <MetricCard
                    title="WACC"
                    value={formatPercentage(company.metrics.wacc_percentual)}
                    icon={BarChart3}
                    subtitle="Custo de capital"
                />
                <MetricCard
                    title="EVA (%)"
                    value={formatPercentage(company.metrics.eva_percentual)}
                    icon={Activity}
                    trend={company.metrics.eva_percentual}
                    subtitle="Valor econômico adicionado"
                    className={company.metrics.eva_percentual >= 0 ? "border-l-4 border-l-emerald-500" : "border-l-4 border-l-red-500"}
                />
                <MetricCard
                    title="Upside (%)"
                    value={formatPercentage(company.metrics.upside_percentual)}
                    icon={TrendingUp}
                    trend={company.metrics.upside_percentual}
                    subtitle="Potencial de valorização"
                    className={company.metrics.upside_percentual >= 0 ? "border-l-4 border-l-emerald-500" : "border-l-4 border-l-red-500"}
                />
                <MetricCard
                    title="Score Combinado"
                    value={company.metrics.combined_score?.toFixed(2)}
                    icon={Zap}
                    subtitle="Pontuação geral"
                    className="border-l-4 border-l-blue-500"
                />
            </div>

            {/* Análise com IA */}
            <Card className="shadow-lg">
                <CardHeader className="pb-4">
                    <div className="flex items-center space-x-2">
                        <BrainCircuit className="h-5 w-5 text-purple-600" />
                        <CardTitle className="text-xl">Análise Qualitativa com IA</CardTitle>
                    </div>
                    <CardDescription>
                        Análise profissional baseada nos indicadores financeiros, gerada pela API do Gemini.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Button 
                        onClick={handleGenerateAiAnalysis} 
                        disabled={isAiLoading}
                        className="mb-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                    >
                        {isAiLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Analisando...
                            </>
                        ) : (
                            <>
                                <Sparkles className="mr-2 h-4 w-4" />
                                Gerar Análise
                            </>
                        )}
                    </Button>
                    
                    {aiError && (
                        <Alert variant="destructive" className="mb-4">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{aiError}</AlertDescription>
                        </Alert>
                    )}
                    
                    {aiAnalysis && (
                        <div className="mt-4 p-6 bg-slate-50 rounded-lg border">
                            <div 
                                className="prose prose-slate max-w-none"
                                dangerouslySetInnerHTML={{ 
                                    __html: aiAnalysis
                                        .replace(/## (.*?)/g, '<h3 class="text-lg font-semibold text-slate-800 mb-2 mt-4">$1</h3>')
                                        .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-700">$1</strong>')
                                        .replace(/\n/g, '<br>')
                                }} 
                            />
                        </div>
                    )}
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

    const fetchAllData = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/v1/ranking/full');
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Erro na API: ${response.status} - ${errorText}`);
            }
            const data = await response.json();
            
            if (!data || !data.full_ranking_data) {
                 throw new Error('A API retornou dados em um formato inesperado.');
            }
            
            setFullAnalysisReport(data);

            if (data.full_ranking_data.length > 0) {
                setCurrentTicker(data.full_ranking_data[0].ticker);
            }
        } catch (err) {
            console.error('Erro ao buscar dados:', err);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchAllData();
    }, []);

    const navigateToDetails = (ticker) => {
        setCurrentTicker(ticker);
        setCurrentView('details');
    };

    const retryFetch = () => {
        fetchAllData();
    };

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
                <LoadingSpinner />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
                <ErrorDisplay error={error} onRetry={retryFetch} />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                                <div className="p-2 bg-blue-600 rounded-lg">
                                    <BarChart3 className="h-6 w-6 text-white" />
                                </div>
                                <div>
                                    <h1 className="text-xl font-bold text-slate-900">Valuation Ibovespa</h1>
                                    <p className="text-xs text-slate-500">Sistema de Análise Financeira</p>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center space-x-2">
                            <div className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-sm font-medium">
                                ✓ Online
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Tabs value={currentView} onValueChange={setCurrentView} className="space-y-6">
                    <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:grid-cols-3 bg-white shadow-sm">
                        <TabsTrigger value="overview" className="flex items-center space-x-2">
                            <PieChart className="h-4 w-4" />
                            <span>Visão Geral</span>
                        </TabsTrigger>
                        <TabsTrigger value="ranking" className="flex items-center space-x-2">
                            <BarChart3 className="h-4 w-4" />
                            <span>Ranking</span>
                        </TabsTrigger>
                        <TabsTrigger value="details" className="flex items-center space-x-2">
                            <Building2 className="h-4 w-4" />
                            <span>Detalhes</span>
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="overview" className="space-y-6">
                        <OverviewView 
                            report={fullAnalysisReport} 
                            navigateToDetails={navigateToDetails} 
                        />
                    </TabsContent>

                    <TabsContent value="ranking" className="space-y-6">
                        <RankingView 
                            data={fullAnalysisReport?.full_ranking_data || []} 
                            navigateToDetails={navigateToDetails} 
                        />
                    </TabsContent>

                    <TabsContent value="details" className="space-y-6">
                        <DetailsView 
                            allData={fullAnalysisReport?.full_ranking_data || []} 
                            ticker={currentTicker} 
                            setCurrentTicker={setCurrentTicker} 
                        />
                    </TabsContent>
                </Tabs>
            </main>

            {/* Footer */}
            <footer className="bg-white border-t border-slate-200 mt-16">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                        <div className="text-sm text-slate-500">
                            © 2025 Sistema de Análise Financeira. Dados do Ibovespa via yfinance.
                        </div>
                        <div className="mt-2 md:mt-0 text-sm text-slate-500">
                            Última atualização: {fullAnalysisReport?.timestamp ? new Date(fullAnalysisReport.timestamp).toLocaleString('pt-BR') : 'N/A'}
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}

export default App;
