import ccxt, time, config, sys, math

exchange = ccxt.ftx({
    'apiKey':config.API_KEY,
    'secret':config.SECRET_KEY,
    'headers': {'FTX-SUBACCOUNT': 'FundingRate'}
})

ticker = exchange.fetch_ticker(config.SYMBOL)

# 每格有向上多少錢
each_grid_num = (config.upper_limit - config.lower_limit)/config.grid_num
# 計算要要掛多少買賣單
lower_buy_lines = math.ceil((ticker['bid'] - config.lower_limit)/each_grid_num) # 多少條買單
upper_sell_lines = config.grid_num - lower_buy_lines - 1 # 多少條賣單

buy_orders = []
sell_orders = []

# 一開始沒有現貨可以賣，所以要市價買入  這邊稍微計算一下要準備多少U
print(input(f'You have to prepare {ticker["bid"] * config.POSITION_SIZE * upper_sell_lines}'))
# initial_buy_order = exchange.create_market_buy_order(config.SYMBOL, config.POSITION_SIZE * upper_sell_lines)

# 掛買單
for i in range(lower_buy_lines):
    price = ticker['bid'] - (each_grid_num * (i+1))  # 從市價出發，向下掛買單
    # price = config.lower_limit + (each_grid_num * i) # 從下限價格出發，向上掛買單
    print('submitting market limit buy order at {}'.format(price))
    order = exchange.create_limit_buy_order(config.SYMBOL, config.POSITION_SIZE ,price)
    buy_orders.append(order['info'])


# 掛賣單
for i in range(upper_sell_lines):
    price = ticker['bid'] + (each_grid_num * (i+1)) # 市價出發，向上買
    # price = config.lower_limit + each_grid_num * lower_buy_lines + each_grid_num * (i+1)
    print('submitting market limit sell order at {}'.format(price))
    order = exchange.create_limit_sell_order(config.SYMBOL, config.POSITION_SIZE ,price)
    sell_orders.append(order['info'])


while True:
    closed_order_ids = []

    for buy_order in buy_orders: #買完一單後，補上賣單
        print('checking buy order'.format(buy_order['id']))
        try:
            order = exchange.fetch_order(buy_order['id'])
        except Exception as e:
            print("request failed, retrying")
            continue

        order_info = order['info']

        if order_info['status'] == config.CLOSED_ORDER_STATUS: # 紀錄有掛單被執行
            closed_order_ids.append(order_info['id'])
            print('buy order executed at {}'.format(order_info['price']))
            new_sell_price = float(order_info['price']) + each_grid_num
            print('create new limit sell order at {}'.format(new_sell_price))
            new_sell_order = exchange.create_limit_sell_order(config.SYMBOL, config.POSITION_SIZE, new_sell_price)
            sell_orders.append(new_sell_order)

        time.sleep(config.CHECK_ORDERS_FREQUENCY)

    for sell_order in sell_orders:
        print('checking for sell order'.format(sell_order['id']))
        try:
            order = exchange.fetch_order(sell_order['id'])
        except Exception as e:
            print("request failed, retrying")
            continue

        order_info = order['info']

        if order_info['status'] == config.CLOSED_ORDER_STATUS:
            closed_order_ids.append(order_info['id'])
            print('sell order executed at {}'.format(order_info['price']))
            new_buy_price = float(order_info['price']) - each_grid_num
            print('create new limit sell order at {}'.format(new_buy_price))
            new_buy_order = exchange.create_limit_buy_order(config.SYMBOL, config.POSITION_SIZE, new_buy_price)
            buy_orders.append(new_buy_order)

        time.sleep(config.CHECK_ORDERS_FREQUENCY)

    for order_id in closed_order_ids:
            buy_orders = [buy_order for buy_order in buy_orders if buy_order['id'] != order_id]
            sell_orders = [sell_order for sell_order in sell_orders if sell_order['id'] != order_id]

    if len(sell_orders) == 0:
        sys.exit("stopping bot, nothing left to sell ")
