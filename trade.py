'''
    Created on Tue June 19, 2018
    Author: Macingo
    Content: Kucoin API Trading
    API Doc: https://kucoinapidocs.docs.apiary.io
'''

######
# Trade in BTC market
######
import base64
import hashlib
import hmac
import requests
import time
from datetime import datetime

host = 'https://api.kucoin.com'
api_pub = ''
api_pri = ''


# Get time in milliseconds from current Date
def dt_to_ms(dt):
    epoch = datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(delta.total_seconds() * 1000)


# Create Header for authentication
def auth_header(endpoint, query_str):
    # Set current date time
    now = datetime.utcnow()
    nonce = str(dt_to_ms(now))

    str_for_sign = (endpoint + '/' + nonce + '/' + query_str).encode('utf-8')
    sign_result = hmac.new(api_pri.encode('utf-8'), base64.b64encode(str_for_sign), hashlib.sha256)

    signature = sign_result.hexdigest()
    header = {
        'Accept': 'application/json',
        'KC-API-KEY': api_pub,
        'KC-API-NONCE': nonce,
        'KC-API-SIGNATURE': signature
    }
    return header


# Get the whole balances of the account
def get_balance(symbol):
    endpoint = '/v1/account/' + symbol + '/balance'
    query_str = ''
    r = requests.get(host + endpoint + query_str, headers=auth_header(endpoint, query_str))
    return r.json()['data']['balance']


# Get last btc price of a coin
def get_last_btc_price(symbol):
    endpoint = '/v1/open/tick'
    r = requests.get(host + endpoint)
    tickers = r.json()['data']
    for ticker in tickers:
        if ticker['symbol'] == symbol + '-BTC':
            return float(ticker['lastDealPrice'])


# Get last eth price of a coin
def get_last_eth_price(symbol):
    endpoint = '/v1/open/tick'
    r = requests.get(host + endpoint)
    tickers = r.json()['data']
    for ticker in tickers:
        if ticker['symbol'] == symbol + '-ETH':
            return float(ticker['lastDealPrice'])


# Get last usdt price of a coin
def get_last_usdt_price(symbol):
    endpoint = '/v1/open/tick'
    r = requests.get(host + endpoint)
    tickers = r.json()['data']
    for ticker in tickers:
        if ticker['symbol'] == symbol + '-USDT':
            return float(ticker['lastDealPrice'])


# Initialization forg trading
def input_module():
    print('--- Kucoin API Trading ---')
    cPair = input('>> What\'s your trading pair? (ETHBTC) ')
    cPair = cPair.upper()
    quote_currency = cPair[0:len(cPair) - 3]
    base_currency = cPair[len(cPair) - 3:len(cPair)]

    # set sell_amount
    sell_amount = 0.0
    print('>> Querying Kucoin...')
    current_quote_balance = get_balance(quote_currency)
    sell_all = input('>> Do you want to SELL ALL of %s (%s) y/n ' % (quote_currency, current_quote_balance))
    if sell_all == 'y':
        sell_amount = float(current_quote_balance)
    elif sell_all == 'n':
        sell_amount = input('>> So, how much %s are you SELLING? ' %quote_currency)
        sell_amount = float(sell_amount)
    else:
        exit('Error: invalid input!')
    # if sell_amount > current_quote_balance or sell_amount <= 0: # double check on input
    #     exit('Error: insufficient sell_amount!')

    # set limit_sell_price
    limit_sell_price_base = input('>> What\'s your price base? (USD/BTC/ETH) ')
    limit_sell_price_base = limit_sell_price_base.upper()
    limit_sell_price = input('>> What\'s your limit price for SELLING? (in %s) ' %limit_sell_price_base)
    limit_sell_price = float(limit_sell_price)
    print('>> Querying Kucoin...')

    limit_usd = base_price_convertor(limit_sell_price_base, limit_sell_price)['usd']
    limit_eth = base_price_convertor(limit_sell_price_base, limit_sell_price)['eth']
    limit_btc = base_price_convertor(limit_sell_price_base, limit_sell_price)['btc']
    if limit_sell_price:
        print('>> You will sell %s %s into %s at price >= USD %s -- BTC %s -- ETH %s'
              % (str(sell_amount), quote_currency, base_currency, str(limit_usd), str(limit_btc), str(limit_eth)))

    # set time_gap and
    time_gap = int(input('>> What is your time gap between each trade? (in seconds) '))
    print('--- Input Ends ---\n')

    # Final confirmation
    x = input('>> Start Trading? y/n ')
    if not x or x == 'n':
        exit('>> Trading Canceled!')
    y = input('>> Are you confirmed? y/n ')
    if not y or y == 'n':
        exit('>> Trading Canceled!')

    # integrate input into json and pass to execution
    initialization_json = {
        'cPair': quote_currency + '-' + base_currency,
        'quote_currency': quote_currency,
        'base_currency': base_currency,
        'sell_amount': sell_amount,
        'price_base': limit_sell_price_base,
        'limit_price': limit_sell_price,
        'time_gap': time_gap
    }

    return initialization_json


# Base price convertor
def base_price_convertor(base_currency, base_price):
    usd = 0.0
    btc = 0.0
    eth = 0.0
    if base_currency == 'USD':
        usd = str(base_price)
        btc = str('%.8f' %(base_price / get_last_usdt_price('BTC')))
        eth = str('%.8f' %(base_price / get_last_usdt_price('ETH')))
    elif base_currency == 'BTC':
        btc = str(base_price)
        usd = str('%.8f' %(base_price * get_last_usdt_price('BTC')))
        eth = str('%.8f' %(base_price / get_last_btc_price('ETH')))
    elif base_currency == 'ETH':
        eth = str(base_price)
        usd = str('%.8f' %(base_price * get_last_usdt_price('ETH')))
        btc = str('%.8f' %(base_price * get_last_btc_price('ETH')))

    else:
        exit('Error: base currency should be USD/BTC/ETH!')
    return {
        'usd': usd,
        'eth': eth,
        'btc': btc
    }


# Get info on highest BID and lowest ASK
def get_highest_bid(quote_crypto, base_crypto):
    r = requests.get(host + '/v1/open/orders-buy?symbol=' + quote_crypto + '-' + base_crypto)
    bid_json = {
        'price': r.json()['data'][0][0],
        'amount': r.json()['data'][0][1],
        'volume_in_base_crypto': r.json()['data'][0][2]
    }
    return bid_json


# Place limit order for the highest bid, if it's in our favour
def place_limit_order(cPair, side, price, amount):
    endpoint = '/v1/'+cPair+'/order'
    data = {'type':side, 'amount':amount, 'price':price}
    query_str = 'amount=' + str(amount) + '&price=' + str(price) + '&type=' + side
    r = requests.post(host + endpoint, params=data, headers=auth_header(endpoint, query_str))
    return r.json()


# Execute trades within single function
'''
    config_json = {
        'cPair': cPair,
        'quote_currency': quote_currency,
        'base_currency': base_currency,
        'sell_amount': sell_amount,
        'price_base': limit_sell_price_base,
        'limit_price': limit_sell_price,
        'time_gap': time_gap
    }
'''
def trade_execution(initialization_json):
    print('\n--- Trading Starts ---\n')
    config_json = initialization_json
    sold_amount = 0.0
    while sold_amount < config_json['sell_amount']:
        limit_btc_price = float(base_price_convertor(config_json['price_base'], config_json['limit_price'])['btc'])
        # limit_eth_price = base_price_convertor(config_json['price_base'], config_json['limit_price'])['eth']
        trade_pair = config_json['quote_currency'] + '-' + 'BTC'

        highest_bid = get_highest_bid(config_json['quote_currency'], 'BTC')

        highest_bid_price = float(highest_bid['price'])
        highest_bid_amount = float(highest_bid['amount'])
        highest_bid_volume_in_base_crypto = float(highest_bid['volume_in_base_crypto'])

        if limit_btc_price <= highest_bid_price:
            if highest_bid_volume_in_base_crypto <= 0.1:
                place_limit_order(trade_pair, 'SELL', highest_bid_price, highest_bid_amount)
                sold_amount += highest_bid_amount
            else:
                max_amount = (0.1 / highest_bid_volume_in_base_crypto) * highest_bid_amount
                place_limit_order(trade_pair, 'SELL', highest_bid_price, max_amount)
                sold_amount += max_amount
            time.sleep(config_json['time_gap'])


# Main
trade_execution(input_module())
