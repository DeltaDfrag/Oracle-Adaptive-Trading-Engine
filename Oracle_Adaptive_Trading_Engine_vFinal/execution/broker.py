
def place_order(symbol: str, quantity: int, side: str):
    print(f"[BROKER] {side.upper()} {quantity} of {symbol}")
    return {"status": "ok"}
