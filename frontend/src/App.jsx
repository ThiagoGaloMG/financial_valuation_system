import { useState, useEffect } from 'react';
import { Button } from './components/ui/button.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card.jsx';
import { Input } from './components/ui/input.jsx';
import { Label } from './components/ui/label.jsx';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs.jsx';
import { Badge } from './components/ui/badge.jsx';
import { Alert, AlertDescription } from './components/ui/alert.jsx';
import { Loader2, TrendingUp, TrendingDown, DollarSign, BarChart3, PieChart, Target, Info, Zap, Activity } from 'lucide-react';
import Chart from 'chart.js/auto'; // Importa Chart.js
import './App.css'; 
import './index.css';

// =======================================================================================
// CORREÇÃO PRINCIPAL AQUI:
// A URL base agora é lida da variável de ambiente VITE_API_BASE_URL.
// Isso permite que a URL seja diferente em desenvolvimento e em produção (no Render).
// =======================================================================================
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [companyData, setCompanyData] = useState(null); // Para análise de empresa única
  const [fullAnalysisReport, setFullAnalysisReport] = useState(null); // Para relatório completo/rápido
  const [tickerInput, setTickerInput] = useState(''); // Input para buscar empresa única
  const [activeTab, setActiveTab] = useState('dashboard'); // Estado da aba ativa

  // Instâncias dos gráficos Chart.js
  const [scatterChartInstance, setScatterChartInstance] = useState(null);
  const [top10ChartInstance, setTop10ChartInstance] = useState(null);
  
  // Formatação de valores
  const formatCurrency = (value) => {
    if (value === null || isNaN(value)) return 'N/A';
    if (Math.abs(value) >= 1e9) {
      return `R$ ${(value / 1e9).toFixed(2)}B`;
    }
    if (Math.abs(value) >= 1e6) {
      return `R$ ${(value / 1e6).toFixed(2)}M`;
    }
    if (Math.abs(value) >= 1e3) {
      return `R$ ${(value / 1e3).toFixed(2)}K`;
    }
    return `R$ ${value.toFixed(2)}`;
  };

  const formatPercentage = (value) => {
    if (value === null || isNaN(value)) return 'N/A';
    return `${value.toFixed(2)}%`;
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleDateString('pt-BR');
  };

  // Função para buscar dados da API
  const fetchAnalysis = async (endpoint, options = {}) => {
    setLoading(true);
    setError('');
    try {
      // Nenhuma alteração aqui, já usa a API_BASE_URL corretamente.
      const response = await fetch(`<span class="math-inline">\{API\_BASE\_URL\}</span>{endpoint}`, options);
      if (!response.ok) {
        // Tenta ler a mensagem de erro do backend se houver
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            errorData = { message: `Erro no servidor: ${response.statusText}` };
        }
        throw new Error(errorData.message || 'Erro na requisição da API');
      }
      const data = await response.json();
      return data;
    } catch (err) {
      console.error("Erro ao buscar dados:", err);
      setError(`Erro: ${err.message}. Verifique a URL da API e o status do backend.`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Funções de Handler para os botões
  const handleRunQuickAnalysis = async () => {
    // CORREÇÃO APLICADA: O endpoint não precisa mais de /analyze
    const report = await fetchAnalysis('/complete', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_companies: 15 }),
    });
    if (report) {
      setFullAnalysisReport(report);
      setCompanyData(null); 
      setActiveTab('dashboard'); 
    }
  };

  const handleRunFullAnalysis = async () => {
    // CORREÇÃO APLICADA: O endpoint não precisa mais de /analyze
    const report = await fetchAnalysis('/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_companies: null }),
    });
    if (report) {
      setFullAnalysisReport(report);
      setCompanyData(null);
      setActiveTab('dashboard');
    }
  };

  const handleSearchCompany = async () => {
    if (!tickerInput) {
      setError('Por favor, insira um ticker para buscar.');
      return;
    }
    // CORREÇÃO APLICADA: O endpoint não precisa mais de /analyze
    const data = await fetchAnalysis(`/company/${tickerInput.toUpperCase().trim()}`);
    if (data) {
      setCompanyData(data);
      setFullAnalysisReport(null);
      setActiveTab('company-details');
    }
  };
  
  // Efeito para criar/atualizar gráficos (sem alterações aqui)
  useEffect(() => {
    // Dashboard Scatter Chart
    if (activeTab === 'dashboard' && fullAnalysisReport && fullAnalysisReport.full_report_data) {
        const ctx = document.getElementById('scatterChart');
        if (!ctx) return;

        if (scatterChartInstance) {
            scatterChartInstance.destroy();
        }

        const chartData = fullAnalysisReport.full_report_data.map(c => ({
            x: c.eva_percentual,
            y: c.efv_percentual,
            label: c.ticker,
            company_name: c.company_name,
        }));

        const newScatterChart = new Chart(ctx.getContext('2d'), {
            type: 'scatter',
            data: {
            datasets: [{
                label: 'Empresas',
                data: chartData,
                backgroundColor: 'rgba(59, 130, 246, 0.7)',
                borderColor: 'rgba(37, 99, 235, 1)',
                pointRadius: 6,
                pointHoverRadius: 9,
            }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const company = context.raw;
                                return `<span class="math-inline">\{company\.label\} \(</span>{company.company_name}): EVA: ${company.x?.toFixed(2)}%, EFV: ${company.y?.toFixed(2)}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'EVA (%) - Criação de Valor Atual',
                            font: { weight: 'bold' }
                        },
                        grid: { color: '#e2e8f0' }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'EFV (%) - Potencial de Valor Futuro',
                            font: { weight: 'bold' }
                        },
                        grid: { color: '#e2e8f0' }
                    }
                }
            }
        });
        setScatterChartInstance(newScatterChart);
    }

    // Top 10 Bar Chart
    if (activeTab === 'top10' && fullAnalysisReport && fullAnalysisReport.rankings && fullAnalysisReport.rankings.top_10_combined) {
        const ctx = document.getElementById('top10Chart');
        if (!ctx) return;

        if (top10ChartInstance) {
            top10ChartInstance.destroy();
        }

        const top10Data = fullAnalysisReport.rankings.top_10_combined.map(c => ({
            ticker: c.ticker,
            score: c.combined_score
        })).sort((a, b) => a.score - b.score);

        const newTop10Chart = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: top10Data.map(c => c.ticker),
                datasets: [{
                    label: 'Score Combinado',
                    data: top10Data.map(c => c.score),
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgba(37, 99, 235, 1)',
                    borderWidth: 1,
                    borderRadius: 5,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.raw?.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Score de Valuation',
                            font: { weight: 'bold' }
                        },
                        grid: { color: '#e2e8f0' }
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            }
        });
        setTop10ChartInstance(newTop10Chart);
    }

    // Limpeza
    return () => {
        if (scatterChartInstance) scatterChartInstance.destroy();
        if (top10ChartInstance) top10ChartInstance.destroy();
    };
  }, [activeTab, fullAnalysisReport]);

  const RenderRankingTable = ({ data, title, description }) => {
    if (!data || data.length === 0) {
        return (
            <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>Nenhum dado disponível para este ranking.</AlertDescription>
            </Alert>
        );
    }

    const [sortedData, setSortedData] = useState(data);
    const [sortColumn, setSortColumn] = useState('combined_score');
    const [sortOrder, setSortOrder] = useState('desc');

    useEffect(() => {
        const dataToSort = [...data];
        dataToSort.sort((a, b) => {
            const valA = a[sortColumn];
            const valB = b[sortColumn];
            if (valA === null || isNaN(valA)) return sortOrder === 'asc' ? 1 : -1;
            if (valB === null || isNaN(valB)) return sortOrder === 'asc' ? -1 : 1;
            if (typeof valA === 'string' && typeof valB === 'string') {
                return sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
            }
            return sortOrder === 'asc' ? valA - valB : valB - valA;
        });
        setSortedData(dataToSort);
    }, [data, sortColumn, sortOrder]);

    const handleHeaderClick = (column) => {
        if (column === sortColumn) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortColumn(column);
            setSortOrder('desc');
        }
    };

    const getSortIndicator = (column) => {
        if (column === sortColumn) {
            return sortOrder === 'asc' ? ' ▲' : ' ▼';
        }
        return '';
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Pos.</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('ticker')}>Ticker {getSortIndicator('ticker')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('company_name')}>Empresa {getSortIndicator('company_name')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('combined_score')}>Score {getSortIndicator('combined_score')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('eva_percentual')}>EVA (%) {getSortIndicator('eva_percentual')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('efv_percentual')}>EFV (%) {getSortIndicator('efv_percentual')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('upside_percentual')}>Upside (%) {getSortIndicator('upside_percentual')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('riqueza_atual')}>Riqueza Atual {getSortIndicator('riqueza_atual')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('riqueza_futura')}>Riqueza Futura {getSortIndicator('riqueza_futura')}</th>
                                <th className="table-header-sortable px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider" onClick={() => handleHeaderClick('market_cap')}>Market Cap {getSortIndicator('market_cap')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200">
                            {sortedData.map((company, index) => (
                                <tr key={company.ticker} className="hover:bg-slate-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{index + 1}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{company.ticker}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-800">{company.company_name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-blue-600">{company.combined_score?.toFixed(2) || 'N/A'}</td>
                                    <td className={`px-6 py-4 whitespace-nowrap text-sm ${company.eva_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>{formatPercentage(company.eva_percentual)}</td>
                                    <td className={`px-6 py-4 whitespace-nowrap text-sm ${company.efv_percentual > 0 ? 'text-blue-600' : 'text-red-600'}`}>{formatPercentage(company.efv_percentual)}</td>
                                    <td className={`px-6 py-4 whitespace-nowrap text-sm ${company.upside_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>{formatPercentage(company.upside_percentual)}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{formatCurrency(company.riqueza_atual)}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{formatCurrency(company.riqueza_futura)}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{formatCurrency(company.market_cap)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
  };
  
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 antialiased">
      <div className="container mx-auto p-4 md:p-8 max-w-6xl">
        <header className="text-center mb-8">
            <h1 className="text-3xl md:text-4xl font-bold text-slate-900">Sistema de Análise Financeira</h1>
            <p className="text-slate-600 mt-2">Valuation de Empresas do Ibovespa (EVA & EFV)</p>
        </header>

        <main>
            {error && (
                <Alert className="mb-4 bg-red-100 border-red-400 text-red-700">
                    <Info className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {loading && (
                <div className="flex justify-center items-center h-32">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                    <span className="ml-2 text-blue-600">Calculando...</span>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>Análise Rápida / Completa</CardTitle>
                        <CardDescription>Analise as principais empresas ou o Ibovespa completo.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-3">
                        <Button onClick={handleRunQuickAnalysis} disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white shadow-md">
                            <Zap className="mr-2 h-4 w-4" />
                            Análise Rápida (15 Empresas)
                        </Button>
                        <Button onClick={handleRunFullAnalysis} disabled={loading} className="w-full bg-slate-700 hover:bg-slate-800 text-white shadow-md">
                            <Activity className="mr-2 h-4 w-4" />
                            Análise Completa (Ibovespa)
                        </Button>
                    </CardContent>
                </Card>

                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>Análise por Ticker</CardTitle>
                        <CardDescription>Obtenha uma análise detalhada de uma empresa específica.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-3">
                        <Label htmlFor="ticker">Ticker da Empresa (Ex: PETR4.SA)</Label>
                        <Input
                            id="ticker"
                            type="text"
                            placeholder="Ex: VALE3.SA"
                            value={tickerInput}
                            onChange={(e) => setTickerInput(e.target.value)}
                            className="border-slate-300 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <Button onClick={handleSearchCompany} disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white shadow-md">
                            <Info className="mr-2 h-4 w-4" />
                            Buscar Empresa
                        </Button>
                    </CardContent>
                </Card>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-4 bg-slate-200">
                    <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
                    <TabsTrigger value="full-ranking">Ranking Completo</TabsTrigger>
                    <TabsTrigger value="top10">Top 10 Ações</TabsTrigger>
                    <TabsTrigger value="company-details" disabled={!companyData}>Empresa Detalhada</TabsTrigger>
                </TabsList>
                
                {/* O restante do código de renderização das abas permanece o mesmo */}
                <TabsContent value="dashboard" className="mt-4">
                  <div className="space-y-6">
                    <p className="text-slate-700 leading-relaxed">
                      Bem-vindo ao Painel de Análise de Valuation. Esta seção oferece uma visão geral das principais métricas do Ibovespa, destacando a criação de valor e o potencial futuro das empresas.
                      Utilize os cartões de métricas para um resumo rápido e o gráfico de dispersão para identificar padrões e oportunidades no mercado.
                    </p>
                    {fullAnalysisReport && fullAnalysisReport.summary_statistics ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <Card className="metric-card">
                          <h3>Empresas Analisadas</h3>
                          <p>{fullAnalysisReport.total_companies_analyzed}</p>
                        </Card>
                        <Card className="metric-card">
                          <h3>Criando Valor (EVA &gt; 0)</h3>
                          <p className="text-green-600">{fullAnalysisReport.summary_statistics.positive_eva_count}</p>
                        </Card>
                        <Card className="metric-card">
                          <h3>Potencial Futuro (EFV &gt; 0)</h3>
                          <p className="text-blue-600">{fullAnalysisReport.summary_statistics.positive_efv_count}</p>
                        </Card>
                        <Card className="metric-card">
                          <h3>Data da Análise</h3>
                          <p>{formatDate(fullAnalysisReport.timestamp)}</p>
                        </Card>
                      </div>
                    ) : (
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription>Execute uma análise (Rápida ou Completa) para ver o Dashboard.</AlertDescription>
                      </Alert>
                    )}

                    {fullAnalysisReport && fullAnalysisReport.full_report_data && (
                      <Card>
                        <CardHeader>
                          <CardTitle>Dispersão EVA vs. EFV</CardTitle>
                          <CardDescription>
                            Este gráfico ajuda a identificar empresas com forte criação de valor atual (EVA) e alto potencial futuro (EFV).
                            O quadrante superior direito representa as empresas ideais.
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="chart-container">
                            <canvas id="scatterChart"></canvas>
                          </div>
                        </CardContent>
                      </Card>
                    )}
                    
                    {fullAnalysisReport && fullAnalysisReport.portfolio_suggestion && (
                        <Card>
                            <CardHeader>
                                <CardTitle>Sugestão de Portfólio (Moderado)</CardTitle>
                                <CardDescription>
                                    Uma alocação de exemplo baseada em uma combinação de EVA e EFV.
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center text-sm font-medium text-slate-700">
                                        <span>EVA do Portfólio:</span>
                                        <span className={fullAnalysisReport.portfolio_suggestion.portfolio_eva_pct > 0 ? 'text-green-600' : 'text-red-600'}>
                                            {formatPercentage(fullAnalysisReport.portfolio_suggestion.portfolio_eva_pct)} ({formatCurrency(fullAnalysisReport.portfolio_suggestion.portfolio_eva_abs)})
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        {Object.entries(fullAnalysisReport.portfolio_suggestion.weights).map(([ticker, weight]) => (
                                            <div key={ticker} className="flex items-center">
                                                <span className="text-sm font-medium text-slate-700 w-1/4">{ticker}</span>
                                                <div className="w-3/4 bg-slate-200 rounded-full h-3">
                                                    <div
                                                        className="bg-blue-500 h-3 rounded-full"
                                                        style={{ width: `${(weight * 100).toFixed(1)}%` }}
                                                    ></div>
                                                </div>
                                                <span className="ml-2 text-sm font-medium w-12 text-right">
                                                    {(weight * 100).toFixed(1)}%
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                  </div>
                </TabsContent>

                <TabsContent value="full-ranking" className="mt-4">
                  <p className="text-slate-700 leading-relaxed mb-6">
                      Nesta aba, você encontra o ranking completo de todas as empresas analisadas, com detalhes sobre cada métrica.
                      Clique nos cabeçalhos das colunas para ordenar a tabela e identificar as empresas que se destacam em diferentes aspectos de valuation.
                  </p>
                  {fullAnalysisReport && fullAnalysisReport.full_report_data ? (
                    <RenderRankingTable data={fullAnalysisReport.full_report_data} title="Ranking Completo das Empresas" description="Ordene pela métrica desejada para encontrar as melhores oportunidades." />
                  ) : (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>Execute uma análise (Rápida ou Completa) para ver o Ranking Completo.</AlertDescription>
                    </Alert>
                  )}
                </TabsContent>

                <TabsContent value="top10" className="mt-4">
                  <p className="text-slate-700 leading-relaxed mb-6">
                      Explore aqui as 10 melhores empresas por diferentes critérios de valuation. Esta visão consolidada permite uma rápida identificação das empresas com maior potencial de criação de valor e valorização futura, conforme as métricas de EVA, EFV e Upside.
                  </p>
                  {fullAnalysisReport && fullAnalysisReport.rankings ? (
                    <div className="space-y-6">
                      <Card>
                        <CardHeader>
                          <CardTitle>Top 10 Melhores Ações (Score Combinado)</CardTitle>
                          <CardDescription>As 10 empresas com melhor pontuação combinada, considerando EVA, EFV e Upside. Representam as oportunidades mais atraentes.</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="chart-container">
                            <canvas id="top10Chart"></canvas>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle>Empresas Criadoras de Valor (EVA &gt; 0)</CardTitle>
                          <CardDescription>Empresas que geraram valor econômico positivo para seus acionistas.</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <ul className="list-disc list-inside space-y-2">
                            {fullAnalysisReport.opportunities?.value_creators?.length > 0 ? (
                              fullAnalysisReport.opportunities.value_creators.map(([ticker, eva_pct]) => (
                                <li key={ticker} className="flex justify-between items-center">
                                  <span className="font-medium text-slate-800">{ticker}</span>
                                  <Badge className="bg-green-100 text-green-800">{formatPercentage(eva_pct)} EVA</Badge>
                                </li>
                              ))
                            ) : (
                              <li>Nenhuma empresa com EVA positivo encontrada.</li>
                            )}
                          </ul>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle>Empresas com Potencial de Crescimento (EFV &gt; 0)</CardTitle>
                          <CardDescription>Empresas com expectativa de criação de valor futuro.</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <ul className="list-disc list-inside space-y-2">
                            {fullAnalysisReport.opportunities?.growth_potential?.length > 0 ? (
                              fullAnalysisReport.opportunities.growth_potential.map(([ticker, efv_pct]) => (
                                <li key={ticker} className="flex justify-between items-center">
                                  <span className="font-medium text-slate-800">{ticker}</span>
                                  <Badge className="bg-blue-100 text-blue-800">{formatPercentage(efv_pct)} EFV</Badge>
                                </li>
                              ))
                            ) : (
                              <li>Nenhuma empresa com EFV positivo encontrada.</li>
                            )}
                          </ul>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle>Empresas Subvalorizadas (Upside &gt; 20%)</CardTitle>
                          <CardDescription>Ações com potencial significativo de valorização de acordo com o modelo.</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <ul className="list-disc list-inside space-y-2">
                            {fullAnalysisReport.opportunities?.undervalued?.length > 0 ? (
                              fullAnalysisReport.opportunities.undervalued.map(([ticker, upside_pct]) => (
                                <li key={ticker} className="flex justify-between items-center">
                                  <span className="font-medium text-slate-800">{ticker}</span>
                                  <Badge className="bg-purple-100 text-purple-800">{formatPercentage(upside_pct)} Upside</Badge>
                                </li>
                              ))
                            ) : (
                              <li>Nenhuma empresa subvalorizada encontrada.</li>
                            )}
                          </ul>
                        </CardContent>
                      </Card>
                    </div>
                  ) : (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>Execute uma análise (Rápida ou Completa) para ver os rankings TOP 10.</AlertDescription>
                    </Alert>
                  )}
                </TabsContent>
                
                <TabsContent value="company-details" className="mt-4">
                  <p className="text-slate-700 leading-relaxed mb-6">
                      Esta seção apresenta os detalhes da análise de valuation para a empresa específica que você buscou. Aqui, você pode mergulhar nas métricas de EVA, EFV, Riqueza e Upside, entendendo a saúde financeira e o potencial da companhia individualmente.
                  </p>
                  {companyData ? (
                    <Card>
                      <CardHeader>
                        <CardTitle>{companyData.company_name} ({companyData.ticker})</CardTitle>
                        <CardDescription>Análise Detalhada de Valuation</CardDescription>
                      </CardHeader>
                      <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">Market Cap</h3>
                          <p className="text-2xl font-bold text-slate-900">{formatCurrency(companyData.metrics.market_cap)}</p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">Preço da Ação</h3>
                          <p className="text-2xl font-bold text-slate-900">{formatCurrency(companyData.metrics.stock_price, 'R$ ')}</p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">WACC</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.wacc_percentual !== null ? 'text-slate-900' : 'text-slate-500'}`}>
                            {formatPercentage(companyData.metrics.wacc_percentual)}
                          </p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">EVA (Absoluto)</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.eva_abs > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(companyData.metrics.eva_abs)}
                          </p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">EVA (%)</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.eva_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatPercentage(companyData.metrics.eva_percentual)}
                          </p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">EFV (Absoluto)</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.efv_abs > 0 ? 'text-blue-600' : 'text-red-600'}`}>
                            {formatCurrency(companyData.metrics.efv_abs)}
                          </p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">EFV (%)</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.efv_percentual > 0 ? 'text-blue-600' : 'text-red-600'}`}>
                            {formatPercentage(companyData.metrics.efv_percentual)}
                          </p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">Riqueza Atual</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.riqueza_atual > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(companyData.metrics.riqueza_atual)}
                          </p>
                        </div>
                        <div className="metric-card p-4">
                          <h3 className="text-sm font-medium text-slate-500">Riqueza Futura</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.riqueza_futura > 0 ? 'text-blue-600' : 'text-red-600'}`}>
                            {formatCurrency(companyData.metrics.riqueza_futura)}
                          </p>
                        </div>
                        <div className="metric-card p-4 col-span-full">
                          <h3 className="text-sm font-medium text-slate-500">Upside Potencial</h3>
                          <p className={`text-2xl font-bold ${companyData.metrics.upside_percentual > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatPercentage(companyData.metrics.upside_percentual)}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  ) : (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>Nenhuma empresa selecionada. Use a caixa de busca acima.</AlertDescription>
                    </Alert>
                  )}
                </TabsContent>

            </Tabs>
        </main>
      </div>
    </div>
  );
}

export default App;
