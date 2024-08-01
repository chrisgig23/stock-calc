import yfinance as yf

def fetch_current_prices(positions):
    prices = {}
    for position in positions:
        ticker = position.name
        stock = yf.Ticker(ticker)
        prices[ticker] = stock.history(period="1d")['Close'].iloc[-1]
    return prices