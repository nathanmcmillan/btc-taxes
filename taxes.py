import sys
import csv
from operator import itemgetter
from datetime import datetime

debug = False
epoch = datetime(1970, 1, 1)


class Trade:
    def __init__(self, size, price):
        self.size = size
        self.price = price


def main():
    if len(sys.argv) <= 3:
        print("strategy? coinbase path? binance path?")
        return

    strategy = sys.argv[1]
    coinbase_path = sys.argv[2]
    binance_path = sys.argv[3]

    trades = []

    try:
        with open(coinbase_path, newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            header = next(reader, None)
            if debug:
                print(header)
            for row in reader:
                time = datetime.strptime(row[3], "%Y-%m-%dT%H:%M:%S.%fZ")
                time = int((time - epoch).total_seconds())
                del row[3]
                row.insert(0, time)
                row.insert(0, "COINBASE")
                trades.append(row)
    except FileNotFoundError:
        print(coinbase_path, "not found")
        return

    try:
        with open(binance_path, newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            header = next(reader, None)
            if debug:
                print(header)
            for row in reader:
                time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                row[0] = int((time - epoch).total_seconds())
                row.insert(0, "BINANCE")
                trades.append(row)
    except FileNotFoundError:
        print(binance_path, "not found")
        return

    trades.sort(key=itemgetter(1))

    import usd
    coin_data = usd.CoinData("coinbase/BTC-USD.txt", "coinbase/ETH-USD.txt", "binance")

    gains = 0.0
    history = dict()
    for row in trades:
        if debug:
            print(row)
        if row[0] == "COINBASE":
            side = row[4]
            size = float(row[5])
            coin = row[6]
            price = float(row[7])
            if side == "BUY":
                if coin not in history:
                    history[coin] = list()
                history[coin].append(Trade(size, price))
                print("bought {:,.2f} {} at $ {:,.2f}".format(size, coin, price))
            else:
                delete = list()
                coin_history = history[coin]
                if strategy == "LIFO":
                    coin_history = coin_history[:]
                    coin_history.reverse()

                if len(coin_history) == 0:
                    raise Exception("something went wrong")

                for trade in coin_history:
                    if trade.size >= size:
                        trade.size -= size
                        profit = (size * price) - (size * trade.price)
                        gains += profit
                        if profit >= 0.0:
                            print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} profit $ {:,.2f}".format(size, coin, price, trade.price, profit))
                        else:
                            print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} lost $ {:,.2f}".format(size, coin, price, trade.price, -profit))
                        if trade.size == 0.0:
                            delete.append(trade)
                        break
                    else:
                        profit = (trade.size * price) - (trade.size * trade.price)
                        gains += profit
                        if profit >= 0.0:
                            print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} profit $ {:,.2f}".format(trade.size, coin, price, trade.price, profit))
                        else:
                            print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} lost $ {:,.2f}".format(trade.size, coin, price, trade.price, -profit))
                        size -= trade.size
                        trade.size = 0
                        delete.append(trade)

                for trade in delete:
                    history[coin].remove(trade)

        elif row[0] == "BINANCE":
            time = row[1]
            market = row[2]
            side = row[3]
            size = float(row[5])
            total = float(row[6])
            fee_coin = row[8]

            buy_coin = fee_coin
            sold_coin = market.replace(fee_coin, "")

            if side == "BUY":
                sold_size = total
                buy_size = size
            else:
                sold_size = size
                buy_size = total

            buy_coin_usd = coin_data.get_usd_value(time, buy_coin)
            sold_coin_usd = coin_data.get_usd_value(time, sold_coin)

            delete = list()
            coin_history = history[sold_coin]
            if strategy == "LIFO":
                coin_history = coin_history[:]
                coin_history.reverse()

            if len(coin_history) == 0:
                raise Exception("something went wrong")

            for trade in coin_history:
                if trade.size >= sold_size:
                    trade.size -= sold_size
                    profit = (sold_size * sold_coin_usd) - (sold_size * trade.price)
                    gains += profit
                    if profit >= 0.0:
                        print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} profit $ {:,.2f}".format(sold_size, sold_coin, sold_coin_usd, trade.price, profit))
                    else:
                        print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} lost $ {:,.2f}".format(sold_size, sold_coin, sold_coin_usd, trade.price, -profit))
                    if trade.size == 0.0:
                        delete.append(trade)
                    break
                else:
                    profit = (trade.size * sold_coin_usd) - (trade.size * trade.price)
                    gains += profit
                    if profit >= 0.0:
                        print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} profit $ {:,.2f}".format(trade.size, sold_coin, sold_coin_usd, trade.price, profit))
                    else:
                        print("sold {:,} {} at $ {:,.2f} bought at $ {:,.2f} lost $ {:,.2f}".format(trade.size, sold_coin, sold_coin_usd, trade.price, -profit))
                    sold_size -= trade.size
                    trade.size = 0
                    delete.append(trade)

            for trade in delete:
                history[sold_coin].remove(trade)

            if buy_coin not in history:
                history[buy_coin] = list()
            history[buy_coin].append(Trade(buy_size, buy_coin_usd))

            print("bought {:,} {} ($ {:,.2f}) for {:,} {} ($ {:,.2f})".format(sold_size, sold_coin, sold_coin_usd, buy_size, buy_coin, buy_coin_usd))

    print()
    if gains > 0.0:
        rate = 0.25
        taxes = gains * rate
        print("capital gains $ {:,.3f}, taxes owed $ {:,.3f}".format(gains, taxes))
    else:
        print("capital losses $ {:,.3f}".format(-gains))
    print('----------------------------------------')


print("----------------------------------------")
print("|              coin taxes              |")
print("----------------------------------------")
main()
