import pandas as pd
import numpy as np

def generate_dummy_data(days=500):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq='B')
    # Random walk
    returns = np.random.normal(0.0005, 0.01, size=days)
    price = 10000 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        'open': price,
        'high': price * 1.01,
        'low': price * 0.99,
        'close': price * (1 + np.random.normal(0, 0.005, days)),
        'volume': np.random.randint(100000, 1000000, days)
    }, index=dates)

    df.index = df.index.tz_localize("Asia/Kolkata")
    return df

def test_fallback():
    print("Generating dummy data for test mode")
    df = generate_dummy_data()
    return df
