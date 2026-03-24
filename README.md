# CYU AM — Dashboard de Gestion de Portefeuille

Dashboard professionnel de suivi et d'analyse de portefeuille financier multi-asset, developpe dans le cadre du Master 2 GIF (CY Tech).

---

## Ce qui a ete realise

### Infrastructure et donnees

- **Base de donnees SQLite** avec 6 tables : `portfolios`, `transactions`, `market_prices`, `fx_rates`, `assets_info`, `nav_history`. Schema avec foreign keys, index et cache integre.
- **Wrapper yfinance** avec cache SQLite automatique : les prix deja telecharges sont stockes localement, seules les dates manquantes sont fetchees. Couverture : actions, ETF, futures, forex.
- **Module FX** : recuperation des taux de change quotidiens (EURUSD, EURGBP, EURCHF) via yfinance, inversion automatique pour conversion vers EUR, forward-fill sur les jours sans cotation.
- **Univers de 20 actifs** pre-configure : 12 actions (4 secteurs), 4 ETF, 2 matieres premieres, 2 paires forex. Extensible via ticker Yahoo personnalise.

### Portfolio Engine (coeur du systeme)

Algorithme de reconstitution NAV jour par jour :
1. Charge les transactions du portefeuille
2. Pour chaque jour ouvre, applique les achats/ventes
3. Valorise chaque position : `quantite x prix_local x taux_FX`
4. Somme toutes les positions + cash = **NAV quotidienne en EUR**

Gestion multi-devises complete : un portefeuille peut mixer des actifs EUR, USD, GBP et matieres premieres, tout est converti en EUR automatiquement.

Calcul du VWAP (prix moyen pondere) et du P&L realise/latent par position.

### Metriques financieres (28 indicateurs)

**Performance** : rendement total, CAGR, YTD, MTD, rendements mensuels (heatmap-ready), rendements cumules, rendements par periode (1M, 3M, 6M, 1A).

**Risque** : volatilite annualisee, Sharpe, Sortino, Omega, Calmar, Max Drawdown (valeur + duree), VaR 95% (historique et parametrique), CVaR/Expected Shortfall, skewness, kurtosis.

**Benchmark** : Beta, Alpha de Jensen, Tracking Error, Information Ratio, correlation, Up/Down Capture Ratio.

**Rolling** : toutes les metriques ci-dessus sur fenetres glissantes 30j, 90j, 252j.

### Optimisation de portefeuille

- **Portefeuille de variance minimale** (scipy.optimize)
- **Portefeuille Max Sharpe** (tangent portfolio)
- **Frontiere efficiente** : 50 points calcules par resolution sequentielle sous contrainte de rendement cible
- **Simulation Monte Carlo** : jusqu'a 10 000 portefeuilles aleatoires
- Comparaison allocation actuelle vs allocations optimales
- Option vente a decouvert activable

### Reporting PDF

Generation automatique d'un rapport PDF de 5 pages (ReportLab) :

| Page | Contenu |
|------|---------|
| 1 | Page de garde (nom, benchmark, periode) |
| 2 | Resume executif : KPIs + metriques risque + comparaison benchmark par periode |
| 3 | Rendements mensuels : heatmap coloree (vert/rouge) |
| 4 | Analyse des risques : tableau complet 17 metriques en 2 colonnes |
| 5 | Composition : positions actuelles avec P&L + historique des transactions |

Fond noir professionnel sur chaque page, footer avec nom du portefeuille et numero de page. Export en bytes (telechargement Streamlit) ou sauvegarde fichier.

### Dashboard Streamlit (7 pages)

| Page | Description |
|------|-------------|
| **Overview** | 8 KPI cards, courbe NAV base 100 vs benchmark, allocation par classe/actif (pie charts), bar chart performance par actif |
| **Performance** | Tableau comparatif par periode vs benchmark, rendements cumules, heatmap mensuelle, distribution des rendements + courbe normale, underwater chart, rolling volatilite/Sharpe |
| **Risques** | Tableau des 17+ metriques, matrice de correlation entre actifs, VaR en EUR, stress tests (-5% a -30%) |
| **Positions** | Tableau detaille avec P&L colore, graphique chandelier interactif, fiche de l'actif |
| **Transactions** | Creation de portefeuille, saisie de transaction (univers ou custom), import CSV avec template, historique filtrable + export |
| **Optimisation** | Frontiere efficiente + scatter Monte Carlo colore par Sharpe, points Min Variance / Max Sharpe / Actuel, tableau allocations, bar chart poids optimaux |
| **Reporting** | Selection periode (mensuel/trimestriel/custom), apercu, generation PDF, telechargement, sauvegarde sur disque |

Dark mode professionnel : fond `#0E1117`, accents verts `#00D4AA` et bleus `#4A9EFF`, positif `#26A69A`, negatif `#EF5350`.

---

## Comment lancer le dashboard

### Prerequis

Python 3.10+ et pip.

### Installation

```bash
cd "Projet dashboard portfolio"
pip install -r requirements.txt
```

### Lancement

```bash
python -m streamlit run cyu_am/app.py
```

Le dashboard s'ouvre sur `http://localhost:8501`.

### Premier usage

1. Aller dans **Transactions** > onglet "Creer un portefeuille"
2. Renseigner nom, capital initial (ex: 100 000 EUR), date de creation
3. Onglet "Ajouter une transaction" : selectionner un actif dans l'univers CYU AM ou saisir un ticker Yahoo personnalise
4. Revenir sur **Overview** pour voir la NAV, les KPIs et l'allocation
5. Aller dans **Reporting** pour generer un PDF

On peut aussi importer un fichier CSV de transactions (template telechargeable dans l'interface).

---

## Architecture du code

```
cyu_am/
  app.py                         Point d'entree Streamlit
  config/
    settings.py                  Parametres (DB path, couleurs, taux sans risque)
    tickers.py                   Univers de 20 actifs + helpers
    benchmarks.py                4 benchmarks (S&P500, CAC40, MSCI World, EuroStoxx50)
  data/
    database.py                  SQLite : schema, connexion, CRUD
    market_data.py               yfinance + cache SQLite
    fx_data.py                   Taux de change quotidiens
    portfolio_engine.py          Reconstitution NAV multi-asset/multi-devise
  metrics/
    performance.py               Rendements, CAGR, YTD, MTD, heatmap
    risk.py                      28 metriques de risque + risk_summary()
    rolling.py                   Metriques sur fenetres glissantes
    optimization.py              Markowitz, Monte Carlo, frontiere efficiente
  pages/
    1_overview.py                Page vue d'ensemble
    2_performance.py             Page analyse de performance
    3_risk.py                    Page analyse des risques
    4_positions.py               Page detail des positions
    5_transactions.py            Page gestion des transactions
    6_optimization.py            Page optimisation Markowitz
    7_reporting.py               Page generation PDF
  reporting/
    pdf_generator.py             Orchestrateur PDF
    charts_export.py             Plotly vers PNG (necessite kaleido)
    sections/                    5 sections du rapport PDF
  ui/
    components.py                KPI cards, badges, selecteurs
    charts.py                    10 fonctions Plotly
    style.css                    Dark mode CSS
  utils/
    formatters.py                Formatage EUR, %, ratios
```

### Flux de donnees

```
yfinance -----> market_data.py + fx_data.py -----> SQLite (cache)
                                                      |
transactions (SQLite) -----> portfolio_engine.py -----> NAV quotidienne EUR
                                                      |
                              metrics/ (performance, risk, benchmark, rolling)
                                                      |
                              ui/charts.py -----> pages/*.py -----> app.py
                                                      |
                              reporting/pdf_generator.py -----> PDF
```

### Principes de conception

- **Metriques = fonctions pures** : entree DataFrame/Series, sortie scalaire. Faciles a tester.
- **Cache SQLite** : les prix et taux FX sont stockes localement, seules les nouvelles dates sont fetchees.
- **Pas de cle API** : tout est gratuit (yfinance, FRED CSV).
- **Multi-portefeuille** : chaque portefeuille est independant avec ses propres transactions et metriques.
- **Conversion FX centralisee** : la conversion multi-devises se fait dans le portfolio engine, pas dans l'UI.

---

## Dependances

| Package | Role |
|---------|------|
| `streamlit` | Framework dashboard |
| `streamlit-option-menu` | Navigation sidebar avec icones |
| `yfinance` | Donnees de marche (OHLCV, fondamentaux) |
| `plotly` | Graphiques interactifs (dark mode) |
| `pandas` / `numpy` | Manipulation de donnees |
| `scipy` | Optimisation (Markowitz) + distribution normale (VaR) |
| `reportlab` | Generation PDF |
| `openpyxl` | Lecture/ecriture Excel |

---

## Pistes d'amelioration

### Priorite haute

- **Tests unitaires** : ecrire les tests pour `metrics/performance.py`, `metrics/risk.py` et `portfolio_engine.py`. Les metriques sont des fonctions pures, donc tres faciles a tester avec des series synthetiques.
- **Graphiques dans le PDF** : installer `kaleido` (`pip install kaleido`) pour exporter les graphiques Plotly en PNG et les inserer dans le rapport. Le code est deja prepare (`charts_export.py`), il suffit d'appeler `fig_to_temp_file()` et passer le chemin aux sections.
- **Gestion des erreurs yfinance** : certains tickers (ex: `MC.PA`) peuvent remonter "possibly delisted" temporairement. Ajouter un retry avec fallback sur les donnees en cache.

### Priorite moyenne

- **Dividendes et splits** : yfinance avec `auto_adjust=True` ajuste les prix historiques, mais le P&L affiche ne distingue pas le gain en capital du rendement de dividende. Ajouter un tracking separee des dividendes verses.
- **Contribution a la performance** : decomposer le rendement total par actif et par classe d'actif (attribution de performance Brinson).
- **Commentaire de gestion** : ajouter un champ texte libre dans la page Reporting pour que le gerant puisse ecrire un commentaire qui sera inclus dans le PDF.
- **Frontiere efficiente 3D** : ajouter une vue 3D (rendement x volatilite x Sharpe) avec Plotly `Surface` ou `Scatter3d`.
- **Alertes** : notifications quand un actif depasse un seuil de drawdown ou quand le portefeuille s'ecarte trop de l'allocation cible.

### Priorite basse

- **Migration PostgreSQL** : si le projet evolue vers du multi-utilisateur, migrer de SQLite vers PostgreSQL (le schema est compatible).
- **Deploiement Streamlit Cloud** : heberger le dashboard en ligne pour acces distant.
- **DuckDB** : remplacer SQLite par DuckDB pour des requetes analytiques plus performantes sur de gros volumes OHLCV.
- **Backtest integre** : permettre de simuler des strategies de trading (momentum, mean-reversion) directement depuis le dashboard avec les donnees historiques.
- **API REST** : exposer les metriques via une API FastAPI pour integration avec d'autres outils.

---

*Projet Master 2 GIF — CY Tech / CYU Asset Management*
