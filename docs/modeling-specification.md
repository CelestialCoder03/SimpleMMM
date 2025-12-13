# Modeling Specification

## 1. Supported Model Types

### 1.1 Linear Regression (OLS)
- **Use Case**: Baseline model, interpretable coefficients
- **Library**: scikit-learn `LinearRegression`
- **Constraints**: Post-hoc coefficient adjustment only

### 1.2 Ridge Regression (L2 Regularization)
- **Use Case**: Handle multicollinearity, prevent overfitting
- **Library**: scikit-learn `Ridge`
- **Hyperparameters**: 
  - `alpha` (regularization strength)
- **Constraints**: Post-hoc coefficient adjustment

### 1.3 Elastic Net (L1 + L2 Regularization)
- **Use Case**: Feature selection + regularization
- **Library**: scikit-learn `ElasticNet`
- **Hyperparameters**:
  - `alpha` (regularization strength)
  - `l1_ratio` (L1 vs L2 balance)

### 1.4 Bayesian Regression
- **Use Case**: Incorporate prior knowledge, uncertainty quantification
- **Library**: PyMC v5
- **Features**:
  - Custom priors on coefficients
  - Posterior distributions for uncertainty
  - MCMC sampling with diagnostics

---

## 2. Constraint System

### 2.1 Coefficient Constraints

#### Sign Constraints
```yaml
constraints:
  tv_spend:
    sign: positive  # coefficient must be >= 0
  competitor_price:
    sign: negative  # coefficient must be <= 0
```

#### Bound Constraints
```yaml
constraints:
  facebook_impressions:
    min: 0.0
    max: 0.5
```

#### Relationship Constraints
```yaml
constraints:
  relationships:
    - type: greater_than
      left: tv_spend
      right: radio_spend  # TV coefficient > Radio coefficient
```

### 2.2 Contribution Constraints

#### Single Variable Contribution
```yaml
contribution_constraints:
  instagram_impressions:
    max_contribution_pct: 1.5  # Max 1.5% of total sales
    min_contribution_pct: 0.0
```

#### Group Contribution Constraints
```yaml
contribution_constraints:
  groups:
    - name: media_atl
      variables:
        - tv_spend
        - radio_spend
        - print_spend
      max_contribution_pct: 10.0  # Combined max 10% of total
      min_contribution_pct: 2.0
    
    - name: digital
      variables:
        - facebook_spend
        - google_spend
        - instagram_spend
      max_contribution_pct: 15.0
```

### 2.3 Implementation Approach

| Model Type | Constraint Method |
|------------|-------------------|
| OLS | Constrained optimization (scipy.optimize.minimize) |
| Ridge | Constrained optimization with L2 penalty |
| Bayesian | Prior specification (truncated distributions) |

---

## 3. Prior Specification (Bayesian Models)

### 3.1 Supported Prior Distributions

| Distribution | Parameters | Use Case |
|--------------|------------|----------|
| Normal | μ (mean), σ (std) | General coefficients |
| HalfNormal | σ (std) | Positive-only coefficients |
| TruncatedNormal | μ, σ, lower, upper | Bounded coefficients |
| Uniform | lower, upper | No prior knowledge |
| Exponential | λ (rate) | Positive coefficients |
| Beta | α, β | Proportion parameters |

### 3.2 Prior Configuration Example
```yaml
priors:
  tv_spend:
    distribution: truncated_normal
    params:
      mu: 0.3
      sigma: 0.1
      lower: 0.0
      upper: 1.0
  
  intercept:
    distribution: normal
    params:
      mu: 1000000
      sigma: 500000
  
  # Group prior (hierarchical)
  media_group:
    type: hierarchical
    variables: [tv_spend, radio_spend, digital_spend]
    hyperprior:
      mu: normal(0.2, 0.1)
      sigma: half_normal(0.05)
```

---

## 4. Data Granularity Support

### 4.1 Granularity Levels

| Level | Description | Example Dimensions |
|-------|-------------|-------------------|
| National | Aggregate country-level | Date |
| Regional | State/Province level | Date × Region |
| City | City-level granularity | Date × City |
| Channel | By sales channel | Date × Channel |
| Regional + Channel | Combined | Date × Region × Channel |

### 4.2 Hierarchical Modeling

For multi-granularity data, support hierarchical/mixed-effects models:

```
National Model:
  y_national = β₀ + Σ βᵢxᵢ + ε

Regional Model:
  y_region = β₀ + β₀_region + Σ (βᵢ + βᵢ_region)xᵢ + ε
  
  where:
  - β₀_region ~ Normal(0, σ_region)
  - βᵢ_region ~ Normal(0, σᵢ_region)
```

### 4.3 Granularity Configuration
```yaml
model_config:
  granularity:
    level: regional_channel
    dimensions:
      - name: region
        column: state_code
        type: categorical
      - name: channel
        column: sales_channel
        type: categorical
    
    # How to handle hierarchy
    hierarchy_type: partial_pooling  # Options: no_pooling, complete_pooling, partial_pooling
    
    # Which coefficients vary by dimension
    varying_coefficients:
      by_region: [tv_spend, local_radio]
      by_channel: [digital_spend, promo_discount]
      fixed: [seasonality, holiday_flag]
```

---

## 5. Adstock & Saturation Transformations

### 5.1 Adstock (Carryover Effect)
```
adstock(x, θ) = x_t + θ·adstock(x, θ)_{t-1}

Parameters:
- θ (decay rate): 0 < θ < 1
```

### 5.2 Saturation (Diminishing Returns)

#### Hill Function
```
hill(x, K, S) = x^S / (K^S + x^S)

Parameters:
- K (half-saturation point)
- S (slope)
```

#### Logistic Function
```
logistic(x, L, k, x₀) = L / (1 + exp(-k(x - x₀)))
```

### 5.3 Transformation Configuration
```yaml
transformations:
  tv_spend:
    adstock:
      type: geometric
      decay: 0.7  # or fit from data
      max_lag: 8
    saturation:
      type: hill
      params:
        K: auto  # fit from data
        S: auto
  
  digital_spend:
    adstock:
      type: weibull
      shape: 2.0
      scale: 3.0
    saturation:
      type: logistic
```

---

## 6. Model Output & Metrics

### 6.1 Goodness of Fit
- R² (coefficient of determination)
- Adjusted R²
- RMSE (Root Mean Square Error)
- MAPE (Mean Absolute Percentage Error)
- AIC / BIC (for model comparison)

### 6.2 Coefficient Analysis
- Point estimates with confidence intervals
- Standardized coefficients (beta weights)
- VIF (Variance Inflation Factor) for multicollinearity

### 6.3 Contribution Analysis
- Absolute contribution by variable
- Percentage contribution to total
- Time series decomposition
- Waterfall charts

### 6.4 Bayesian Diagnostics (when applicable)
- Posterior distributions
- Credible intervals (HDI)
- R-hat convergence diagnostics
- Effective sample size
- Posterior predictive checks

---

## 7. Visualization & Charts (pyecharts)

### 7.1 Chart Types

| Chart | Description | Use Case |
|-------|-------------|----------|
| **Decomposition Stack/Area** | Stacked area chart showing contribution breakdown over time | Visualize how each variable contributes to total sales |
| **Actual vs Fitted Line** | Dual line chart comparing true sales to model predictions | Model fit assessment |
| **Contribution Waterfall** | Waterfall chart showing incremental contribution | Executive summary, channel impact |
| **Coefficients Table** | Interactive table with estimates, CI, p-values | Detailed coefficient analysis |
| **Response Curves** | Line charts showing diminishing returns | Saturation analysis per channel |
| **ROI Curves** | Marginal ROI by spend level | Budget optimization insights |
| **Posterior Distribution** | Density plots for Bayesian coefficients | Uncertainty visualization |

### 7.2 Chart Configuration
```yaml
chart_config:
  theme: "light"  # or "dark"
  color_palette: "default"  # customizable
  interactive: true
  
  decomposition_chart:
    type: "stacked_area"  # or "stacked_bar"
    show_total_line: true
    
  actual_vs_fitted:
    show_residuals: false
    confidence_band: true
    
  waterfall:
    sort_by: "contribution"  # or "alphabetical"
    show_percentages: true
```

---

## 8. Export & Download

### 8.1 Supported Export Formats

| Format | Content | Library |
|--------|---------|--------|
| **HTML** | Interactive charts + report | pyecharts native |
| **PDF** | Static report with charts | WeasyPrint |
| **Excel** | Decomposition data, coefficients | openpyxl |
| **PNG/SVG** | Individual charts | pyecharts snapshot |

### 8.2 Excel Export Structure
```
model_results.xlsx
├── Summary              # Model metrics, R², MAPE
├── Coefficients         # Variable, estimate, CI, p-value
├── Decomposition        # Date, base, var1, var2, ..., total
├── Contributions        # Variable, total, percentage
└── Response Curves      # Spend levels, response values
```

### 8.3 PDF Report Sections
1. Executive Summary
2. Model Configuration
3. Goodness of Fit Metrics
4. Contribution Analysis (waterfall)
5. Decomposition Over Time (stacked area)
6. Response Curves
7. Coefficient Details
8. Appendix: Technical Diagnostics

---

## 9. Model Versioning & Comparison

### 9.1 Version Tracking
- Each model run is versioned
- Store: config, data snapshot hash, results, metrics
- Compare multiple model versions side-by-side

### 9.2 Comparison Metrics
```yaml
comparison:
  metrics:
    - r_squared
    - adjusted_r_squared
    - mape
    - aic
  visualization:
    - coefficient_comparison_plot
    - contribution_comparison_chart
    - residual_comparison
```

---

## 10. Seasonality Configuration

Seasonality features capture cyclical patterns in the data:
- **Weekly patterns**: Weekend vs weekday effects
- **Monthly patterns**: Beginning/middle/end of month
- **Annual patterns**: Quarters, months, holidays

### 10.1 Calendar Features (Explicit Dummies)

Interpretable dummy variables generated automatically:

```yaml
seasonality:
  enabled: true
  method: calendar
  calendar:
    include_weekend: true      # is_weekend binary
    include_month: true        # month_1 ~ month_12
    include_quarter: false     # quarter_1 ~ quarter_4
    include_day_of_week: false # dow_0 ~ dow_6
```

### 10.2 Fourier Features (Smooth Cycles)

Automatic periodic pattern detection:

```yaml
seasonality:
  enabled: true
  method: fourier
  fourier:
    periods: [7, 30, 365]  # Weekly, monthly, annual
    n_terms: 3             # Number of sin/cos pairs per period
```

### 10.3 Combined Approach

Both methods can be used together for comprehensive seasonality modeling:

```yaml
seasonality:
  enabled: true
  method: both
  calendar:
    include_weekend: true
    include_month: true
  fourier:
    periods: [365]
    n_terms: 2
```

---

## 11. Dummy Variables (Event Effects)

Dummy variables capture discrete events and their impact on the target:
- **Calendar events**: Chinese New Year, National Day, Singles Day (11.11)
- **Regional events**: Local promotions, exhibitions
- **Custom periods**: COVID lockdown, supply chain disruptions

### 11.1 Implementation Approach

Users add dummy columns (0/1) in their dataset before upload:

1. Create dummy columns in Excel/CSV (e.g., `cny_2020`, `covid_lockdown`)
2. Upload or update the dataset
3. Mark variables as "control" type in Variable Management
4. Include in model configuration

### 11.2 Dataset Update for New Dummies

When adding new dummy variables:

```
POST /projects/{id}/datasets/{id}/update
Content-Type: multipart/form-data

{
  file: <csv_file>,
  mode: "replace" | "new_version",
  preserve_metadata: true
}
```

Response includes detected column changes:
```json
{
  "dataset_id": "...",
  "added_columns": ["cny_2020", "covid_lockdown"],
  "removed_columns": [],
  "row_count_change": 0
}
```

### 11.3 Model Configuration Reuse

Apply existing model configuration to updated datasets:

```
POST /projects/{id}/models/{id}/apply-to-dataset
{
  "target_dataset_id": "...",
  "new_name": "Model v2 with holidays"
}
```
