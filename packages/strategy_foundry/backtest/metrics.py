import numpy as np

def calculate_cagr(start_val, end_val, years):
    if years <= 0: return 0.0
    if start_val <= 0: return 0.0
    return (end_val / start_val) ** (1/years) - 1

def calculate_sharpe(returns, rf=0.0):
    vol = np.std(returns)
    if vol == 0: return 0.0
    return (np.mean(returns) - rf) / vol * np.sqrt(252)
