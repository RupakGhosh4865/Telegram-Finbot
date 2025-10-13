import asyncio
import os
import sys
import traceback

# Ensure project src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.data.gomarket_client import GoMarketClient


async def main():
    print("Starting GoMarket symbols test (exchange=binance, market_type=spot)")
    try:
        client = GoMarketClient()
        async with client:
            symbols = await client.get_symbols('binance', 'spot')
            print(f"Success: retrieved {len(symbols)} symbols")
            # Print a few
            for s in (symbols[:20] if isinstance(symbols, list) else []):
                print(s)
            
                # After listing symbols, try fetching ticker for BTCUSDT using different formats
            test_symbols = ['BTCUSDT', 'BTC/USDT', 'btc-usdt']
            for ts in test_symbols:
                try:
                    ticker = await client.get_ticker('binance', ts)
                    print(f"Ticker for {ts}: bid={ticker.bid_price}, ask={ticker.ask_price}, last={ticker.last_price}")
                except Exception as e:
                    print(f"Failed to fetch ticker for {ts}: {e}")
    except Exception as e:
        print("Error during GoMarket API call:")
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
