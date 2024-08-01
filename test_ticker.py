import yfinance as yf

def validate_ticker(ticker):
    stock_data = yf.Ticker(ticker).info
    if 'shortName' in stock_data:
        return True, stock_data.get('shortName', 'Unknown')
    else:
        return False, None
    
def get_ticker_details(ticker):
    return yf.Ticker(ticker).info

# Test with known ticker
ticker = input("Enter ticker symbol: ")
is_valid, name = validate_ticker(ticker)
if is_valid:
    print(f"{ticker} is valid. Stock name: {name}")
    show_details = input('Enter Y to show details: ')
    if show_details == 'Y':
        import pprint
        pprint.pprint(get_ticker_details(ticker))
else:
    print(f"{ticker} is not valid.")