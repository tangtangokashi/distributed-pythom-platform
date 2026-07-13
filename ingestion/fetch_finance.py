"""Download a real Yahoo Finance OHLCV dataset for replay or offline model training.

Example: python ingestion/fetch_finance.py --symbols AAPL TSLA NVDA --period 2y
"""
import argparse
from pathlib import Path

import yfinance as yf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "TSLA", "NVDA"])
    parser.add_argument("--period", default="2y")
    parser.add_argument("--output", default="data/finance")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for symbol in args.symbols:
        frame = yf.download(symbol, period=args.period, auto_adjust=True, progress=False)
        if frame.empty:
            print(f"No data returned for {symbol}")
            continue
        frame.reset_index().to_csv(output / f"{symbol}.csv", index=False)
        print(f"Saved {symbol}: {len(frame)} rows")


if __name__ == "__main__":
    main()

