def map_instrument(symbol: str, context: str = "research") -> str:
    """
    Map internal symbol to context specific symbol.
    Context: research, paper_proxy, live_proxy
    """
    import yaml
    try:
        with open("packages/strategy_foundry/configs/instrument_map.yaml") as f:
            config = yaml.safe_load(f)
            return config.get(context, {}).get(symbol, symbol)
    except Exception:
        return symbol
