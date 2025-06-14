# Sistema de Análise Financeira - Valuation Ibovespa

Este projeto implementa um sistema completo de análise financeira e valuation de empresas do Ibovespa, baseado na metodologia de EVA (Economic Value Added), EFV (Economic Future Value) e análise de direcionadores de valor, conforme detalhado no TCC do autor. O sistema é composto por um backend em Python (Flask) para os cálculos e uma API, e um frontend em React para uma interface de usuário interativa.

## Funcionalidades

* **Coleta de Dados:** Coleta dados financeiros de empresas do Ibovespa via API (yfinance).
* **Cálculo de Métricas:** Calcula EVA (Valor Econômico Adicionado), EFV (Valor Futuro Econômico), Riqueza Atual, Riqueza Futura, WACC (Custo Médio Ponderado de Capital) e Upside (Potencial de Valorização).
* **Ranking de Empresas:** Classifica empresas com base em um score combinado dessas métricas.
* **Análise Avançada:** Identifica criadores de valor, empresas com potencial de crescimento, e sugestões de portfólio.
* **API RESTful:** Backend em Flask que expõe os endpoints para as funcionalidades de análise.
* **Interface Web Interativa:** Frontend em React com um painel de controle (dashboard), ranking completo e detalhe de empresas, utilizando Shadcn/UI e Tailwind CSS.
* **Deploy Automatizado:** Configuração para deploy contínuo no Render (Docker e Blueprint).

## Estrutura do Projeto

```
financial_valuation_system/
├── backend/                  # Código do backend (Python/Flask)
│   ├── src/                  # Módulos Python da aplicação
│   │   ├── routes/           # Definição das rotas da API
│   │   ├── models/           # Modelos de dados (ex: usuário)
│   │   ├── financial_analyzer.py # Coleta de dados e cálculos
│   │   ├── advanced_ranking.py   # Ranking avançado e otimização
│   │   ├── ibovespa_analysis_system.py # Orquestrador da análise
│   │   ├── ibovespa_data.py      # Dados do Ibovespa e Selic
│   │   └── utils.py          # Funções utilitárias
│   ├── main.py               # Ponto de entrada da aplicação Flask
│   ├── requirements.txt      # Dependências Python
│   ├── Dockerfile            # Definição do Docker para o backend
│   └── render.yaml           # Configuração de deploy no Render (inclui frontend)
│
├── frontend/                 # Código do frontend (React)
│   ├── public/               # Arquivos estáticos (ícones, etc.)
│   ├── src/                  # Código fonte do React
│   │   ├── components/ui/    # Componentes de UI (Shadcn/UI)
│   │   ├── App.jsx           # Componente principal da aplicação
│   │   ├── App.css           # Estilos CSS específicos do App
│   │   └── main.jsx          # Ponto de entrada do React
│   ├── index.html            # HTML base da aplicação React
│   ├── package.json          # Dependências Node.js/NPM
│   └── vite.config.js        # Configuração do Vite
│
├── .gitignore                # Arquivos ignorados pelo Git
└── README.md                 # Documentação do projeto
```

## Como Rodar Localmente

### Pré-requisitos

* Python 3.9+
* Node.js e npm (ou yarn)
* Git

### 1. Clonar o Repositório

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd financial_valuation_system
```

### 2. Configurar e Rodar o Backend

```bash
cd backend

# Criar e ativar um ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: .\venv\Scripts\activate

# Instalar as dependências
pip install -r requirements.txt

# Rodar a aplicação Flask (em modo de desenvolvimento)
# O Gunicorn é para produção, para dev, pode-se usar: flask run
# No entanto, o main.py já está configurado para gunicorn,
# então vamos usar o comando do Dockerfile para simular o ambiente de produção.
# Certifique-se de que a porta 5000 esteja livre.
python main.py
# ou para usar gunicorn como em produção (recomendado para teste local de deploy):
# gunicorn -w 4 --threads 2 -b 0.0.0.0:5000 main:app
```
O backend estará rodando em `http://localhost:5000`.

### 3. Configurar e Rodar o Frontend

Abra um **novo terminal** e navegue para o diretório `frontend`:

```bash
cd ../frontend

# Instalar as dependências Node.js
npm install

# Rodar a aplicação React em modo de desenvolvimento
npm run dev
```
O frontend estará rodando em `http://localhost:5173` (ou outra porta disponível). As requisições para `/api` serão automaticamente proxyficadas para o backend em `http://localhost:5000`.

## Deploy no Render

Este projeto está configurado para deploy contínuo no [Render](https://render.com) usando um Blueprint.

1.  **Crie uma Conta no Render:** Se você ainda não tem, crie uma conta em `render.com`.
2.  **Crie um novo Blueprint:** No seu dashboard do Render, clique em "New" -> "Blueprint".
3.  **Conecte seu Repositório Git:** Conecte o repositório onde seu código está hospedado.
4.  **Selecione o `render.yaml`:** O Render detectará automaticamente o arquivo `render.yaml` na raiz do seu diretório `backend/`.
5.  **Ajuste Variáveis de Ambiente:** Verifique e ajuste quaisquer variáveis de ambiente sensíveis (como `SECRET_KEY`) nas configurações dos serviços no Render.
6.  **Deploy:** Confirme e o Render iniciará o processo de build e deploy para o backend (Flask) e o frontend (React) como serviços separados.

O frontend servirá o `index.html` e os recursos estáticos, enquanto o backend servirá a API. A configuração de proxy no frontend (`vite.config.js`) garantirá que, mesmo após o deploy, as chamadas `/api` sejam direcionadas corretamente para o seu serviço de backend.

## Próximos Passos e Melhorias

* **Autenticação de Usuários:** Implementar um sistema de autenticação (ex: com Supabase, Firebase Auth) para gerenciar o acesso e análises personalizadas.
* **Persistência de Dados:** Integrar com um banco de dados (Supabase PostgreSQL, Firestore) para armazenar resultados de análises ou perfis de usuários.
* **Dados em Tempo Real:** Melhorar a coleta de dados para incluir dados financeiros mais recentes ou de fontes adicionais (além do yfinance).
* **Visualizações Avançadas:** Adicionar mais tipos de gráficos e visualizações interativas.
* **Alertas e Notificações:** Implementar um sistema de alertas baseado em critérios de valuation.
* **Testes:** Expandir a cobertura de testes unitários e de integração.
* **Performance:** Otimizar a performance do backend para grandes volumes de dados.

---

**Autor:** Thiago Marques Lopes (Baseado no TCC da UFMG)
**Desenvolvido por:** [Seu Nome / Gemini]
