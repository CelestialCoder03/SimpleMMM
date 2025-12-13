"""Generate synthetic MMM test data based on test plan specifications."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def generate_synthetic_mmm_data(
    n_weeks: int = 104,
    regions: list[str] | None = None,
    channels: list[str] | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic MMM test data.
    
    Args:
        n_weeks: Number of weeks of data per region/channel combination
        regions: List of region names (default: North/South/East/West)
        channels: List of channel names (default: Online/Offline)
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with synthetic MMM data
    """
    if regions is None:
        regions = ["North", "South", "East", "West"]
    if channels is None:
        channels = ["Online", "Offline"]
    
    np.random.seed(seed)
    
    # True coefficients for data generation
    TRUE_COEFFICIENTS = {
        "intercept": 10000,
        "tv_spend": 2.5,
        "digital_spend": 3.2,
        "ooh_spend": 1.8,
        "print_spend": 1.2,
        "promotion_discount": -50,
        "price": -100,
    }
    
    # Adstock decay parameters (for generating realistic data)
    ADSTOCK_DECAY = {
        "tv_spend": 0.7,
        "digital_spend": 0.3,
        "ooh_spend": 0.5,
        "print_spend": 0.4,
    }
    
    records = []
    start_date = datetime(2022, 1, 3)  # Start from Monday
    
    for region in regions:
        for channel in channels:
            # Region and channel specific adjustments
            region_factor = {"North": 1.2, "South": 1.0, "East": 0.9, "West": 1.1}[region]
            channel_factor = {"Online": 1.3, "Offline": 0.8}[channel]
            
            # Initialize adstock values
            adstock = {k: 0.0 for k in ADSTOCK_DECAY}
            
            for week in range(n_weeks):
                date = start_date + timedelta(weeks=week)
                
                # Generate independent variables with realistic patterns
                # TV spend: higher in Q4 for holiday season
                base_tv = np.random.uniform(30000, 80000)
                q4_boost = 1.3 if date.month >= 10 else 1.0
                tv_spend = base_tv * q4_boost
                
                # Digital spend: steady throughout year
                digital_spend = np.random.uniform(20000, 60000)
                
                # OOH spend: higher in summer
                base_ooh = np.random.uniform(10000, 30000)
                summer_boost = 1.2 if 5 <= date.month <= 8 else 1.0
                ooh_spend = base_ooh * summer_boost
                
                # Print spend: declining trend
                print_spend = np.random.uniform(5000, 20000) * (1 - week * 0.002)
                print_spend = max(print_spend, 3000)
                
                # Promotion discount
                promotion_discount = np.random.uniform(0, 20)
                
                # Price: slight seasonal variation
                base_price = 100
                price = base_price + np.random.uniform(-15, 15)
                
                # Seasonality index (Q4 boost, summer dip)
                month = date.month
                if month >= 10:
                    seasonality = 1.3
                elif 6 <= month <= 8:
                    seasonality = 0.9
                else:
                    seasonality = 1.0
                
                # Calculate derived metrics
                tv_grp = tv_spend / 1000  # Assume CPP = 1000
                digital_impressions = digital_spend * 50  # Assume CPM = 20
                
                # Apply adstock transformation for sales calculation
                for key in ADSTOCK_DECAY:
                    spend_val = locals()[key]
                    adstock[key] = spend_val + ADSTOCK_DECAY[key] * adstock[key]
                
                # Calculate sales with true coefficients + adstock effect
                sales = (
                    TRUE_COEFFICIENTS["intercept"]
                    + TRUE_COEFFICIENTS["tv_spend"] * adstock["tv_spend"] * 0.6  # Adstock effect
                    + TRUE_COEFFICIENTS["digital_spend"] * adstock["digital_spend"] * 0.5
                    + TRUE_COEFFICIENTS["ooh_spend"] * adstock["ooh_spend"] * 0.7
                    + TRUE_COEFFICIENTS["print_spend"] * adstock["print_spend"] * 0.8
                    + TRUE_COEFFICIENTS["promotion_discount"] * promotion_discount
                    + TRUE_COEFFICIENTS["price"] * price
                ) * seasonality * region_factor * channel_factor
                
                # Add noise (5% standard deviation)
                sales *= np.random.normal(1.0, 0.05)
                
                records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "region": region,
                    "channel": channel,
                    "sales": round(sales, 2),
                    "tv_spend": round(tv_spend, 2),
                    "tv_grp": round(tv_grp, 2),
                    "digital_spend": round(digital_spend, 2),
                    "digital_impressions": round(digital_impressions, 0),
                    "ooh_spend": round(ooh_spend, 2),
                    "print_spend": round(print_spend, 2),
                    "promotion_discount": round(promotion_discount, 2),
                    "price": round(price, 2),
                    "seasonality": round(seasonality, 2),
                })
    
    df = pd.DataFrame(records)
    return df


def generate_national_data(n_weeks: int = 104, seed: int = 42) -> pd.DataFrame:
    """Generate national-level MMM data (no region/channel split).
    
    This is simpler data for testing basic model functionality.
    """
    np.random.seed(seed)
    
    TRUE_COEFFICIENTS = {
        "intercept": 50000,
        "tv_spend": 2.5,
        "digital_spend": 3.2,
        "ooh_spend": 1.8,
        "print_spend": 1.2,
        "promotion_discount": -50,
        "price": -100,
    }
    
    ADSTOCK_DECAY = {
        "tv_spend": 0.7,
        "digital_spend": 0.3,
        "ooh_spend": 0.5,
        "print_spend": 0.4,
    }
    
    records = []
    start_date = datetime(2022, 1, 3)
    adstock = {k: 0.0 for k in ADSTOCK_DECAY}
    
    for week in range(n_weeks):
        date = start_date + timedelta(weeks=week)
        
        # Generate variables
        q4_boost = 1.3 if date.month >= 10 else 1.0
        tv_spend = np.random.uniform(150000, 400000) * q4_boost
        digital_spend = np.random.uniform(100000, 300000)
        ooh_spend = np.random.uniform(50000, 150000) * (1.2 if 5 <= date.month <= 8 else 1.0)
        print_spend = np.random.uniform(20000, 80000) * (1 - week * 0.002)
        print_spend = max(print_spend, 15000)
        promotion_discount = np.random.uniform(0, 15)
        price = 100 + np.random.uniform(-10, 10)
        
        # Seasonality
        if date.month >= 10:
            seasonality = 1.3
        elif 6 <= date.month <= 8:
            seasonality = 0.9
        else:
            seasonality = 1.0
        
        # Derived metrics
        tv_grp = tv_spend / 1000
        digital_impressions = digital_spend * 50
        
        # Adstock
        for key in ADSTOCK_DECAY:
            spend_val = locals()[key]
            adstock[key] = spend_val + ADSTOCK_DECAY[key] * adstock[key]
        
        # Sales
        sales = (
            TRUE_COEFFICIENTS["intercept"]
            + TRUE_COEFFICIENTS["tv_spend"] * adstock["tv_spend"] * 0.6
            + TRUE_COEFFICIENTS["digital_spend"] * adstock["digital_spend"] * 0.5
            + TRUE_COEFFICIENTS["ooh_spend"] * adstock["ooh_spend"] * 0.7
            + TRUE_COEFFICIENTS["print_spend"] * adstock["print_spend"] * 0.8
            + TRUE_COEFFICIENTS["promotion_discount"] * promotion_discount
            + TRUE_COEFFICIENTS["price"] * price
        ) * seasonality
        
        sales *= np.random.normal(1.0, 0.03)
        
        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "sales": round(sales, 2),
            "tv_spend": round(tv_spend, 2),
            "tv_grp": round(tv_grp, 2),
            "digital_spend": round(digital_spend, 2),
            "digital_impressions": round(digital_impressions, 0),
            "ooh_spend": round(ooh_spend, 2),
            "print_spend": round(print_spend, 2),
            "promotion_discount": round(promotion_discount, 2),
            "price": round(price, 2),
            "seasonality": round(seasonality, 2),
        })
    
    return pd.DataFrame(records)


if __name__ == "__main__":
    output_dir = Path(__file__).parent
    
    # Generate hierarchical data (with region and channel)
    print("Generating hierarchical MMM data...")
    df_hierarchical = generate_synthetic_mmm_data()
    hierarchical_path = output_dir / "synthetic_mmm_data.csv"
    df_hierarchical.to_csv(hierarchical_path, index=False)
    print(f"  Saved to: {hierarchical_path}")
    print(f"  Rows: {len(df_hierarchical)}")
    print(f"  Columns: {list(df_hierarchical.columns)}")
    print(f"  Date range: {df_hierarchical['date'].min()} to {df_hierarchical['date'].max()}")
    print(f"  Regions: {df_hierarchical['region'].unique().tolist()}")
    print(f"  Channels: {df_hierarchical['channel'].unique().tolist()}")
    print()
    
    # Generate national data (no splits)
    print("Generating national MMM data...")
    df_national = generate_national_data()
    national_path = output_dir / "synthetic_mmm_national.csv"
    df_national.to_csv(national_path, index=False)
    print(f"  Saved to: {national_path}")
    print(f"  Rows: {len(df_national)}")
    print(f"  Columns: {list(df_national.columns)}")
    print(f"  Date range: {df_national['date'].min()} to {df_national['date'].max()}")
    print()
    
    # Print data summary
    print("=== Hierarchical Data Summary ===")
    print(df_hierarchical.describe())
    print()
    print("=== National Data Summary ===")
    print(df_national.describe())
