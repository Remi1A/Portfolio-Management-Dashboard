# 📊 CY Tech AM — Cahier des Charges
## Dashboard de Gestion & Suivi de Portefeuille Financier

> **Projet** : Master 2 GIF — CY Tech AM  
> **Stack cible** : Python · Streamlit · yfinance · SQLite · Plotly · ReportLab  
> **Ambition** : Dashboard professionnel dark mode, multi-asset (actions, ETF, obligations, forex, matières premières), avec benchmarking et reporting PDF automatisé mensuel  
> **Saisie des transactions** : manuelle via interface + import CSV/Excel  
> **Périmètre actifs** : Multi-asset — actions, ETF, obligations, forex, matières premières

---

## Table des matières

1. [Vision du projet](#1-vision-du-projet)
2. [Choix technologiques justifiés](#2-choix-technologiques-justifiés)
3. [Fonctionnalités détaillées](#3-fonctionnalités-détaillées)
4. [Architecture du code](#4-architecture-du-code)
5. [Modèle de données (SQLite)](#5-modèle-de-données-sqlite)
6. [Métriques financières implémentées](#6-métriques-financières-implémentées)
7. [Module de reporting PDF](#7-module-de-reporting-pdf)
8. [Design & UX du dashboard](#8-design--ux-du-dashboard)
9. [Plan de développement](#9-plan-de-développement)
10. [Questions prévues par le jury](#10-questions-prévues-par-le-jury)

---

## 1. Vision du projet

### Contexte

CYGIF Asset Management doit remplacer ses processus manuels de reporting par un outil automatisé, fiable et professionnel. Le dashboard **CY Tech AM** est conçu comme un véritable outil institutionnel de gestion de portefeuille, à la frontière entre un terminal Bloomberg simplifié et un rapport mensuel automatisé.

### Objectifs stratégiques

- **Automatiser** la collecte de données de marché et le calcul des métriques
- **Centraliser** toutes les informations de performance dans une interface unique
- **Reconstituer** l'historique exact d'un portefeuille à partir de ses transactions (saisie manuelle ou import CSV)
- **Couvrir tous les types d'actifs** : actions, ETF, obligations, forex, matières premières
- **Normaliser en devise de référence** (EUR) les actifs libellés en devises étrangères
- **Générer** automatiquement des rapports PDF professionnels mensuels pour les clients institutionnels
- **Benchmarker** rigoureusement la performance vs indices de référence (S&P 500, CAC 40, MSCI World…)

---

## 2. Choix technologiques justifiés

### Framework dashboard : Streamlit ✅ (retenu)

Streamlit est le choix optimal pour ce projet pour plusieurs raisons :

| Critère | Streamlit | Dash (Plotly) | Flask + Jinja |
|---|---|---|---|
| Courbe d'apprentissage | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Rendu visuel (avec Plotly) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Intégration Python native | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Dark mode natif | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Adapté projet académique | ✅ | ✅ | ❌ |

> **Alternative sérieuse** : `Panel` (HoloViz) si on veut plus de flexibilité sur les layouts. Mais Streamlit + `streamlit-option-menu` + CSS custom suffit largement pour un dark mode professionnel.

### Données de marché : yfinance ✅

- Gratuit, sans clé API
- Couvre actions mondiales, ETF, indices
- Donne OHLCV quotidien, données fondamentales, dividendes, splits
- Compatible avec pandas directement

```python
import yfinance as yf
ticker = yf.Ticker("AAPL")
hist = ticker.history(period="2y")  # 2 ans d'historique
info = ticker.info  # secteur, market cap, PE ratio...
```

### Couverture multi-asset via yfinance

| Classe d'actif | Exemples de tickers Yahoo | Disponibilité |
|---|---|---|
| **Actions** | `AAPL`, `MC.PA`, `ASML.AS` | ✅ Complet (OHLCV + fondamentaux) |
| **ETF** | `SPY`, `CW8.PA`, `IWDA.AS` | ✅ Complet |
| **Obligations / Taux** | `^TNX` (10Y US), `TLT` (ETF oblig) | ✅ Via ETF ou indices |
| **Forex** | `EURUSD=X`, `GBPUSD=X` | ✅ Cours quotidiens |
| **Matières premières** | `GC=F` (Or), `CL=F` (Pétrole), `SI=F` (Argent) | ✅ Futures |
| **Indices** | `^GSPC` (S&P500), `^FCHI` (CAC40), `URTH` (MSCI World ETF) | ✅ Benchmarks |

> **Gestion multi-devises** : les actifs libellés en USD, GBP, CHF sont convertis quotidiennement en EUR grâce aux paires forex (`EURUSD=X`, `EURGBP=X`, `EURCHF=X`) récupérées en même temps que les prix.

### Base de données : SQLite ✅

SQLite est parfait pour ce projet car :
- Zéro configuration, fichier unique portable (`.db`)
- Requêtes SQL complètes via `sqlite3` ou `SQLAlchemy`
- Performances excellentes pour un usage mono-utilisateur
- Facilement migratable vers PostgreSQL si besoin futur

### Visualisations : Plotly ✅

- Graphiques interactifs (zoom, hover, annotations)
- Thème dark natif (`plotly_dark`)
- Compatible Streamlit nativement via `st.plotly_chart()`
- Candlesticks, heatmaps, surface 3D pour la frontière efficiente

### Génération PDF : ReportLab + WeasyPrint

- **ReportLab** : génération programmatique de tableaux et graphiques en PDF
- **WeasyPrint** : conversion HTML → PDF si on préfère templater en HTML/CSS

---

## 3. Fonctionnalités détaillées

### 3.1 Gestion du portefeuille et des transactions

#### Saisie manuelle des transactions (interface Streamlit)

L'utilisateur peut enregistrer chaque transaction avec les champs suivants :

| Champ | Type | Description |
|---|---|---|
| `date` | DATE | Date d'exécution de l'ordre |
| `ticker` | TEXT | Code Yahoo Finance (ex: `AAPL`, `MC.PA`, `GC=F`, `EURUSD=X`) |
| `asset_class` | ENUM | `EQUITY` / `ETF` / `BOND` / `FOREX` / `COMMODITY` |
| `action` | ENUM | `BUY` / `SELL` |
| `quantité` | FLOAT | Nombre de titres / lots / unités |
| `prix_unitaire` | FLOAT | Prix d'exécution dans la devise de l'actif |
| `devise_actif` | TEXT | Devise de l'actif (`EUR`, `USD`, `GBP`…) |
| `frais` | FLOAT | Frais de courtage |
| `portefeuille_id` | INT | Identifiant du portefeuille cible |

#### Import CSV/Excel

- Template CSV téléchargeable depuis l'interface (pré-rempli avec les colonnes attendues)
- Validation automatique : tickers vérifiés via yfinance, dates cohérentes, quantités > 0
- Détection des doublons et des erreurs avec rapport d'import
- Bouton de mapping de colonnes si le CSV vient d'un broker (Degiro, Interactive Brokers…)

#### Reconstitution historique du portefeuille

C'est la fonctionnalité centrale : à partir de l'historique des transactions, le système recalcule **jour par jour** la valeur exacte du portefeuille, **toutes classes d'actifs confondues et converties en EUR**.

**Algorithme de reconstitution multi-asset :**
```
Pour chaque jour de trading t :
    positions[t] = positions[t-1]
    Appliquer les transactions du jour t (achats/ventes)
    Pour chaque position dans positions[t] :
        prix_local[ticker][t]   = prix_cloture yfinance dans devise_actif
        fx_rate[devise][t]      = taux de change vers EUR du jour t
        valeur_eur[ticker][t]   = quantite × prix_local × fx_rate
    valeur_portefeuille[t] = sum(valeur_eur[ticker][t]) + cash_eur[t]
```

Cela produit une **courbe NAV en EUR** cohérente même pour un portefeuille mixant actifs EUR, USD, GBP et matières premières.

### 3.2 Multi-portefeuilles

Le système gère plusieurs portefeuilles indépendants (ex: "Portefeuille Croissance", "Portefeuille Dividendes", "Benchmark simulé"). Chaque portefeuille a :

- Un nom et une description
- Une devise de référence (EUR, USD…)
- Une date de création et un capital initial
- Un historique de transactions propre
- Des métriques calculées indépendamment

### 3.3 Dashboard principal — Pages Streamlit

#### Page 1 : Vue d'ensemble (`🏠 Overview`)

- **KPI Cards** en haut de page (2 rangées de 4) :
  - Valeur totale du portefeuille (€) + variation J-1
  - Performance totale (% depuis inception)
  - Performance YTD / MTD
  - Sharpe Ratio | Sortino Ratio
  - Max Drawdown | Volatilité annualisée
  - Alpha vs benchmark | Beta
- **Sélecteur de benchmark** en sidebar : S&P 500, CAC 40, MSCI World, Euro Stoxx 50, ou personnalisé
- **Graphique NAV** : courbe de valeur liquidative vs benchmark sélectionné (base 100)
- **Allocation par classe d'actif** : pie chart (Equity / ETF / Obligations / Forex / Commodities)
- **Allocation sectorielle** (pour la partie actions) : treemap interactif
- **Top 5 performers / Bottom 5** du portefeuille (toutes classes confondues)

#### Page 2 : Analyse de performance (`📈 Performance`)

- **Rendements cumulés** vs benchmark sur périodes sélectionnables (1M, 3M, 6M, 1A, YTD, Inception)
- **Tableau comparatif vs benchmark** :

| Période | Portefeuille | S&P 500 | CAC 40 | MSCI World | Excès de rendement |
|---|---|---|---|---|---|
| 1 Mois | | | | | |
| 3 Mois | | | | | |
| YTD | | | | | |
| 1 An | | | | | |
| Inception | | | | | |

- **Rendements mensuels** : heatmap calendrier (style quantopian) + colonne benchmark pour comparaison mois par mois
- **Distribution des rendements** : histogramme + courbe de densité normale
- **Rolling metrics** sur fenêtre glissante (30j, 90j, 252j) : Sharpe, volatilité, Beta vs benchmark
- **Underwater chart** : visualisation des drawdowns dans le temps
- **Performance par classe d'actif** : contribution de chaque classe (actions, ETF, commodities…) à la performance totale

#### Page 3 : Analyse des risques (`⚠️ Risques`)

- **Tableau complet des métriques** de risque (voir section 6)
- **Matrice de corrélation** entre les actifs du portefeuille (heatmap Plotly)
- **Value at Risk (VaR)** historique et paramétrique avec visualisation
- **Contribution au risque** par actif (risk contribution chart)
- **Stress tests** : simulation de choc de marché (-10%, -20%, -30%)

#### Page 4 : Détail des positions (`💼 Positions`)

Tableau interactif avec pour chaque position :

| Colonne | Description |
|---|---|
| Ticker | Code + nom de l'entreprise |
| Secteur | Secteur GICS |
| Quantité | Nombre de titres détenus |
| Prix moyen d'achat | VWAP des transactions |
| Prix actuel | Dernière cotation yfinance |
| Valeur de marché | Quantité × Prix actuel |
| P&L latent (€) | Gain/perte non réalisé |
| P&L latent (%) | En pourcentage |
| Poids dans le portefeuille | % de la valeur totale |
| Beta | Beta vs S&P 500 |

- Graphique en chandelier (candlestick) sur clic d'une ligne
- Fiche détaillée de l'actif (PE ratio, Market Cap, dividende…)

#### Page 5 : Transactions (`📋 Transactions`)

- Historique complet des transactions avec filtres (date, ticker, type)
- Formulaire d'ajout de transaction
- Import/export CSV
- Calcul automatique du P&L réalisé par transaction

#### Page 6 : Optimisation (`🔬 Optimisation`)

- **Frontière efficiente de Markowitz** : graphique interactif 2D (rendement vs volatilité)
- Portefeuille de variance minimale
- Portefeuille de Sharpe maximal
- **Simulation Monte Carlo** : 1000 portefeuilles aléatoires projetés sur la frontière
- Comparaison allocation actuelle vs allocation optimale suggérée

#### Page 7 : Reporting (`📄 Reporting`)

- Sélection de la période du rapport (mensuel, trimestriel, custom)
- Preview du rapport avant génération
- Bouton de génération PDF
- Historique des rapports générés

---

## 4. Architecture du code

```
cyu_am/
│
├── app.py                          # Point d'entrée Streamlit (routing pages)
│
├── config/
│   ├── settings.py                 # Paramètres globaux (DB path, devises, benchmarks)
│   ├── tickers.py                  # Liste des 20 actifs + classes + secteurs
│   └── benchmarks.py               # Définition des benchmarks (tickers Yahoo + labels)
│
├── data/
│   ├── database.py                 # Connexion SQLite, création tables, migrations
│   ├── market_data.py              # Wrapper yfinance : fetch OHLCV, cache, nettoyage
│   ├── fx_data.py                  # Fetch taux de change quotidiens (EURUSD=X etc.)
│   └── portfolio_engine.py         # Reconstitution NAV multi-asset+FX, VWAP, P&L
│
├── metrics/
│   ├── performance.py              # Returns, CAGR, YTD, MTD, contribution par classe
│   ├── risk.py                     # Sharpe, Sortino, Omega, VaR, CVaR, Beta, MDD
│   ├── benchmark.py                # Alpha, Tracking Error, Info Ratio, Up/Down Capture
│   ├── rolling.py                  # Métriques sur fenêtre glissante
│   └── optimization.py             # Markowitz, Monte Carlo, frontière efficiente
│
├── pages/
│   ├── 1_overview.py               # Page vue d'ensemble + sélecteur benchmark
│   ├── 2_performance.py            # Page analyse performance vs benchmark
│   ├── 3_risk.py                   # Page analyse des risques
│   ├── 4_positions.py              # Page détail des positions (multi-asset)
│   ├── 5_transactions.py           # Page transactions (saisie + import CSV)
│   ├── 6_optimization.py           # Page optimisation Markowitz
│   └── 7_reporting.py              # Page génération PDF
│
├── reporting/
│   ├── pdf_generator.py            # Orchestrateur PDF ReportLab
│   ├── sections/
│   │   ├── cover.py                # Page de garde
│   │   ├── executive_summary.py    # Résumé exécutif + benchmarks
│   │   ├── performance_section.py  # NAV, rendements, heatmap
│   │   ├── risk_section.py         # Métriques de risque
│   │   └── positions_section.py    # Composition + transactions
│   └── charts_export.py            # Plotly → PNG pour insertion PDF
│
├── ui/

│   ├── components.py               # KPI cards, tableaux stylisés, badges classe d'actif
│   ├── charts.py                   # Toutes les fonctions Plotly (NAV, heatmap, etc.)
│   └── style.css                   # CSS custom dark mode CYGIF
│
├── utils/
│   ├── validators.py               # Validation tickers, dates, montants, CSV import
│   ├── formatters.py               # Formatage €, %, dates, noms de classe d'actif
│   ├── currency.py                 # Conversion multi-devises via fx_data
│   └── cache.py                    # Cache yfinance/FX avec TTL
│
├── tests/
│   ├── test_metrics.py
│   ├── test_portfolio_engine.py
│   ├── test_fx_conversion.py       # Tests spécifiques à la conversion devise
│   └── test_data.py
│
├── data/
│   └── cyu_am.db                   # Base SQLite
│
├── exports/                        # Rapports PDF générés
├── requirements.txt
└── README.md
```

### Flux de données entre modules

```
yfinance API ──────────────────────┐
     │                             │
     ▼                             ▼
market_data.py              fx_data.py (EURUSD=X, EURGBP=X…)
     │                             │
     └─────────────┬───────────────┘
                   ▼
           database.py (SQLite cache)
                   │
                   ▼
         portfolio_engine.py  ◄──── transactions (SQLite)
         (NAV multi-asset en EUR)
                   │
         ┌─────────┼────────────────┐
         ▼         ▼                ▼
  performance.py  risk.py    benchmark.py
         │         │                │
         └────────►│◄───────────────┘
                   ▼
             ui/charts.py ──► pages/*.py ──► app.py (Streamlit)
                   │
                   └──► reporting/pdf_generator.py ──► rapport_MMMYYYY.pdf
```

---

## 5. Modèle de données (SQLite)

### Table `portfolios`
```sql
CREATE TABLE portfolios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT,
    currency    TEXT DEFAULT 'EUR',
    created_at  DATE NOT NULL,
    initial_cash REAL DEFAULT 0
);
```

### Table `transactions`
```sql
CREATE TABLE transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER REFERENCES portfolios(id),
    date            DATE NOT NULL,
    ticker          TEXT NOT NULL,
    asset_class     TEXT CHECK(asset_class IN ('EQUITY','ETF','BOND','FOREX','COMMODITY')),
    action          TEXT CHECK(action IN ('BUY', 'SELL')),
    quantity        REAL NOT NULL,
    price           REAL NOT NULL,         -- dans la devise de l'actif
    asset_currency  TEXT DEFAULT 'EUR',
    fees            REAL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table `fx_rates` (cache taux de change quotidiens)
```sql
CREATE TABLE fx_rates (
    base_currency   TEXT NOT NULL,   -- ex: 'USD'
    quote_currency  TEXT NOT NULL,   -- ex: 'EUR'
    date            DATE NOT NULL,
    rate            REAL NOT NULL,   -- 1 base = rate × quote
    PRIMARY KEY (base_currency, quote_currency, date)
);
```

### Table `market_prices` (cache)
```sql
CREATE TABLE market_prices (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL NOT NULL,
    volume      INTEGER,
    fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date)
);
```

### Table `assets_info` (cache métadonnées)
```sql
CREATE TABLE assets_info (
    ticker          TEXT PRIMARY KEY,
    name            TEXT,
    sector          TEXT,
    industry        TEXT,
    currency        TEXT,
    market_cap      REAL,
    pe_ratio        REAL,
    dividend_yield  REAL,
    beta            REAL,
    updated_at      TIMESTAMP
);
```

### Table `nav_history` (NAV pré-calculée)
```sql
CREATE TABLE nav_history (
    portfolio_id    INTEGER REFERENCES portfolios(id),
    date            DATE NOT NULL,
    nav             REAL NOT NULL,
    cash            REAL,
    invested_value  REAL,
    PRIMARY KEY (portfolio_id, date)
);
```

---

## 6. Métriques financières implémentées

### Métriques de benchmarking

| Métrique | Description | Module |
|---|---|---|
| **Excès de rendement** | `R_p - R_benchmark` sur chaque période | `performance.py` |
| **Tracking Error** | `std(R_p - R_benchmark) × √252` | `risk.py` |
| **Information Ratio** | `Excès rendement annualisé / Tracking Error` | `risk.py` |
| **Alpha de Jensen** | `R_p - [R_f + β × (R_m - R_f)]` | `risk.py` |
| **Beta** | `Cov(R_p, R_m) / Var(R_m)` — calculé vs chaque benchmark | `risk.py` |
| **Up Capture Ratio** | Rendement portefeuille / Rendement benchmark sur mois haussiers | `risk.py` |
| **Down Capture Ratio** | Rendement portefeuille / Rendement benchmark sur mois baissiers | `risk.py` |
| **Corrélation vs benchmark** | Rolling sur 90j et 252j | `rolling.py` |

> Les benchmarks disponibles sont : S&P 500 (`^GSPC`), CAC 40 (`^FCHI`), MSCI World (`URTH`), Euro Stoxx 50 (`^STOXX50E`), et tout ticker Yahoo personnalisé.

### Métriques de performance

| Métrique | Formule | Module |
|---|---|---|
| Rendement total | `(NAV_final / NAV_initial) - 1` | `performance.py` |
| CAGR | `(NAV_final / NAV_initial)^(1/n) - 1` | `performance.py` |
| YTD / MTD | Rendement depuis début année/mois | `performance.py` |
| Rendements journaliers | `NAV_t / NAV_{t-1} - 1` | `performance.py` |
| Rendements mensuels | Resampling mensuel de la NAV | `performance.py` |

### Métriques de risque

| Métrique | Formule | Module |
|---|---|---|
| **Volatilité annualisée** | `std(rendements) × √252` | `risk.py` |
| **Sharpe Ratio** | `(R_p - R_f) / σ_p` | `risk.py` |
| **Sortino Ratio** | `(R_p - R_f) / σ_downside` | `risk.py` |
| **Omega Ratio** | `∫_{L}^{∞} (1-F(r))dr / ∫_{-∞}^{L} F(r)dr` | `risk.py` |
| **Calmar Ratio** | `CAGR / |Max Drawdown|` | `risk.py` |
| **Max Drawdown** | `max((Peak - Trough) / Peak)` | `risk.py` |
| **Max Drawdown Duration** | Nombre de jours sous le dernier pic | `risk.py` |
| **VaR historique** | Percentile 5% des rendements historiques | `risk.py` |
| **VaR paramétrique** | `μ - 1.645 × σ` (à 95%) | `risk.py` |
| **CVaR / Expected Shortfall** | Moyenne des rendements < VaR | `risk.py` |
| **Beta** | `Cov(R_p, R_m) / Var(R_m)` | `risk.py` |
| **Alpha de Jensen** | `R_p - [R_f + β × (R_m - R_f)]` | `risk.py` |
| **Tracking Error** | `std(R_p - R_benchmark)` | `risk.py` |
| **Information Ratio** | `(R_p - R_b) / Tracking Error` | `risk.py` |
| **Skewness** | Asymétrie de la distribution des rendements | `risk.py` |
| **Kurtosis** | Queues de distribution | `risk.py` |

### Métriques sur fenêtre glissante (rolling)

- Rolling Sharpe (30j, 90j, 252j)
- Rolling Volatility
- Rolling Beta
- Rolling Max Drawdown

---

## 7. Module de reporting PDF

### Structure du rapport mensuel

```
Page 1 — Page de garde
  • Logo CYGIF AM
  • Nom du portefeuille + benchmark de référence
  • Période du rapport (mois/année)
  • Date de génération

Page 2 — Résumé Exécutif
  • Tableau KPIs principaux (performance, risque, Sharpe)
  • Tableau comparatif multi-benchmarks (S&P500, CAC40, MSCI World)
  • Commentaire de gestion (zone texte libre)

Page 3 — Performance vs Benchmark
  • Graphique NAV cumulée base 100 (portefeuille + benchmarks)
  • Tableau des rendements par période vs chaque benchmark
  • Up/Down Capture Ratio — tableau visuel

Page 4 — Rendements mensuels
  • Heatmap calendrier portefeuille
  • Heatmap calendrier benchmark principal
  • Colonne d'excès de rendement mensuel

Page 5 — Analyse des risques
  • Tableau complet des métriques de risque
  • Graphique underwater (drawdown) vs benchmark
  • Distribution des rendements

Page 6 — Composition du portefeuille
  • Double pie chart : allocation par classe d'actif + par secteur
  • Tableau des positions (ticker, classe, poids, P&L, devise)

Page 7 — Analyse individuelle des actifs
  • Performance par actif (bar chart horizontal)
  • Contribution à la performance totale

Page 8 — Annexes
  • Liste complète des transactions du mois
  • Glossaire des indicateurs (destiné aux clients)
  • Avertissements légaux
```

### Génération technique

```python
# reporting/pdf_generator.py

def generate_monthly_report(portfolio_id: int, start_date: str, end_date: str) -> bytes:
    """
    Génère le rapport PDF mensuel pour un portefeuille donné.
    
    Returns:
        bytes: contenu du fichier PDF généré
    """
    ...
```

---

## 8. Design & UX du dashboard

### Thème visuel : Dark Mode Professionnel

- **Fond principal** : `#0E1117` (Streamlit dark natif)
- **Cartes/panneaux** : `#1E2130`
- **Accent primaire** : `#00D4AA` (vert institutionnel)
- **Accent secondaire** : `#4A9EFF` (bleu données)
- **Positif** : `#26A69A`
- **Négatif** : `#EF5350`
- **Texte principal** : `#FAFAFA`
- **Texte secondaire** : `#8892A4`

### KPI Cards — exemple de composant

```python
# ui/components.py

def kpi_card(label: str, value: str, delta: str, delta_positive: bool):
    """Affiche une carte KPI avec valeur principale et variation."""
    color = "#26A69A" if delta_positive else "#EF5350"
    st.markdown(f"""
    <div style="background:#1E2130; padding:16px; border-radius:8px; 
                border-left: 3px solid {color};">
        <p style="color:#8892A4; font-size:12px; margin:0">{label}</p>
        <p style="color:#FAFAFA; font-size:24px; font-weight:700; margin:4px 0">{value}</p>
        <p style="color:{color}; font-size:13px; margin:0">{delta}</p>
    </div>
    """, unsafe_allow_html=True)
```

### Navigation

Utiliser `streamlit-option-menu` pour une sidebar avec icônes :

```python
from streamlit_option_menu import option_menu

with st.sidebar:
    page = option_menu(
        "CY Tech AM", 
        ["Overview", "Performance", "Risques", "Positions", 
         "Transactions", "Optimisation", "Reporting"],
        icons=["house", "graph-up", "shield", "briefcase", 
               "list-ul", "cpu", "file-pdf"],
        default_index=0
    )
```

---

## 9. Plan de développement

### Sprint 1 — Fondations (Semaine 1)
- [ ] Setup projet, virtualenv, requirements.txt
- [ ] Création de la base SQLite et des tables
- [ ] Module `market_data.py` : fetch yfinance + cache
- [ ] Sélection des 20 actions (5 secteurs × 4 titres)
- [ ] Module `portfolio_engine.py` : reconstitution NAV basique

### Sprint 2 — Métriques & Core (Semaine 2)
- [ ] `metrics/performance.py` : tous les indicateurs de rendement
- [ ] `metrics/risk.py` : Sharpe, Sortino, Omega, MDD, VaR, CVaR, Beta
- [ ] Tests unitaires des métriques
- [ ] Interface Streamlit basique (app.py + sidebar)

### Sprint 3 — Dashboard complet (Semaine 3)
- [ ] Page Overview avec KPIs et graphique NAV
- [ ] Page Performance (heatmap, rolling, underwater)
- [ ] Page Positions (tableau interactif + candlestick)
- [ ] Page Transactions (formulaire + historique)
- [ ] Page Risques (corrélations, VaR, stress tests)

### Sprint 4 — Fonctionnalités avancées (Semaine 4)
- [ ] Page Optimisation (Markowitz + Monte Carlo)
- [ ] Module PDF ReportLab complet
- [ ] Page Reporting avec preview et export
- [ ] Import CSV transactions
- [ ] Dark mode CSS finalisé + polish UI

### Sprint 5 — Finalisation (Semaine 5)
- [ ] Documentation des fonctions (docstrings)
- [ ] README complet
- [ ] Tests end-to-end
- [ ] Préparation démo soutenance
- [ ] Génération du rapport PDF exemple

---

## 10. Questions prévues par le jury

**Q : Comment avez-vous structuré votre code ?**
> Architecture modulaire en 7 couches distinctes (config, data, metrics, ui, pages, reporting, utils). Chaque module a une responsabilité unique (principe SRP). Les métriques sont des fonctions pures (entrée DataFrame → sortie scalaire) facilitant les tests unitaires. Un module dédié `benchmark.py` isole toute la logique de comparaison vs indices.

**Q : Quels défis techniques avez-vous rencontrés ?**
> Trois défis majeurs : (1) la reconstitution NAV multi-asset avec conversion quotidienne en EUR — il faut aligner les calendriers de trading qui diffèrent entre NYSE, Euronext et les marchés de matières premières. (2) La gestion des splits d'actions et dividendes (yfinance les intègre automatiquement via `auto_adjust=True`, ce qui peut fausser les P&L si on mélange prix ajustés et prix réels). (3) Le benchmarking cohérent : normaliser en base 100 à la date d'inception du portefeuille, et pas à la date de création du benchmark.

**Q : Comment avez-vous documenté votre code ?**
> Docstrings NumPy-style sur toutes les fonctions avec paramètres typés, README avec guide d'installation, documentation client (glossaire des indicateurs en français accessible aux non-techniciens), convention PEP8 vérifiée avec flake8, et un template CSV d'import commenté.

**Q : Quelle base de données avez-vous choisie et pourquoi ?**
> SQLite pour sa portabilité (fichier unique `.db` livrable avec le projet), sa robustesse pour un usage mono-utilisateur et sa compatibilité native Python sans serveur. Nous avons ajouté une table `fx_rates` pour cacher les taux de change et éviter des appels API excessifs. Alternative envisagée : DuckDB pour des requêtes analytiques plus performantes sur de gros volumes de données OHLCV, ou PostgreSQL pour un déploiement multi-clients en production.

**Q : Comment vos visualisations communiquent-elles les informations clés ?**
> Choix de Plotly pour l'interactivité (zoom, hover, filtres temporels). Le sélecteur de benchmark en sidebar permet de contextualiser instantanément tous les graphiques. La heatmap mensuelle avec colonne d'excès de rendement vs benchmark est particulièrement efficace pour les clients institutionnels. Le code couleur est cohérent partout : vert pour surperformance, rouge pour sous-performance. Le PDF reprend exactement les mêmes visuels en format statique imprimable.

---

## Annexe — Univers d'investissement suggéré (multi-asset, 20+ actifs)

### Actions (12 titres — 4 secteurs)

| Secteur | Ticker | Entreprise | Place | Devise |
|---|---|---|---|---|
| **Technologie** | AAPL | Apple | NASDAQ | USD |
| Technologie | MSFT | Microsoft | NASDAQ | USD |
| Technologie | ASML.AS | ASML | Euronext | EUR |
| Technologie | NVDA | NVIDIA | NASDAQ | USD |
| **Santé** | SAN.PA | Sanofi | Euronext | EUR |
| Santé | NVO | Novo Nordisk | NYSE | USD |
| **Finance** | BNP.PA | BNP Paribas | Euronext | EUR |
| Finance | GS | Goldman Sachs | NYSE | USD |
| **Consommation** | MC.PA | LVMH | Euronext | EUR |
| Consommation | OR.PA | L'Oréal | Euronext | EUR |
| Consommation | AMZN | Amazon | NASDAQ | USD |
| **Énergie** | TTE.PA | TotalEnergies | Euronext | EUR |

### ETF (4 fonds)

| Ticker | Description | Devise |
|---|---|---|
| CW8.PA | Amundi MSCI World | EUR |
| SPY | SPDR S&P 500 | USD |
| IWDA.AS | iShares MSCI World | USD |
| LQD | iShares Corporate Bond | USD |

### Matières premières (2 futures)

| Ticker | Description | Devise |
|---|---|---|
| GC=F | Or (Gold Futures) | USD |
| CL=F | Pétrole brut WTI | USD |

### Forex (2 paires)

| Ticker | Description |
|---|---|
| EURUSD=X | Euro / Dollar US |
| EURGBP=X | Euro / Livre Sterling |

> **Note** : les paires forex servent à la fois d'actifs investissables ET de taux de conversion pour la NAV consolidée en EUR.

---

*Document rédigé dans le cadre du Master 2 GIF — CY Tech / CY Université*  
*Projet CY Tech AM — Dashboard de gestion de portefeuille*
