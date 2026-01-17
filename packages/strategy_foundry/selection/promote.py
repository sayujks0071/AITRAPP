def should_promote(challenger, current_champion):
    # New must beat current blended_score by >= 10%
    # OR reduce MaxDD by >= 5% absolute while not degrading Sharpe meaningfully.

    if not current_champion:
        return True

    challenger_score = challenger.get("score", 0)
    current_score = current_champion.get("score", 0)

    if challenger_score > current_score * 1.1:
        return True

    return False
