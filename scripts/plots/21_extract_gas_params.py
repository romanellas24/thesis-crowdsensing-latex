"""
Per ogni rete disponibile, calcola la mediana di gas_price_gwei e token_usd
per l'anno 2025 e restituisce un dict:
    { "ETH": (gas_gwei, token_usd), "ARB": (...), ... }

Naming convention attesa nella directory:
    {NETWORK}-GAS-PRICE.csv   →  "Date(UTC)", "UnixTimeStamp", "Value (Wei)"
    {token}-usd-max.csv       →  snapped_at, price, market_cap, total_volume

Il mapping NETWORK→token gestisce i nomi divergenti (es. POLY→POL).
"""

import pandas as pd
from pathlib import Path

# Edge case espliciti: nome rete nel gas CSV → prefisso del token CSV
# Se coincidono in lowercase non serve aggiungere nulla qui.
TOKEN_OVERRIDE = {
    "POLY": "POL",   # Polygon ha rinominato MATIC→POL
}

YEAR = 2025


def _load_gas(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df["ts"]       = pd.to_datetime(df["unixtimestamp"], unit="s", utc=True)
    df["gas_gwei"] = df["value (wei)"].astype(float) / 1e9
    mask = df["ts"].dt.year == YEAR
    result = df.loc[mask, "gas_gwei"]
    if result.empty:
        raise ValueError(f"{path.name}: nessun dato per {YEAR}")
    return result


def _load_token(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["snapped_at"], utc=True)
    mask = df["ts"].dt.year == YEAR
    result = df.loc[mask, "price"]
    if result.empty:
        raise ValueError(f"{path.name}: nessun dato per {YEAR}")
    return result


def extract_all(data_dir: str | Path) -> dict[str, tuple[float, float]]:
    d = Path(data_dir)

    gas_files = {
        p.stem.replace("-GAS-PRICE", "").upper(): p
        for p in d.glob("*-GAS-PRICE.csv")
    }

    # Costruisce un index  lowercase_prefix → Path  per i token CSV
    token_index = {p.stem.split("-")[0].lower(): p for p in d.glob("*-usd-max.csv")}

    results: dict[str, tuple[float, float]] = {}

    for network, gas_path in sorted(gas_files.items()):
        token_key = TOKEN_OVERRIDE.get(network, network).lower()
        token_path = token_index.get(token_key)

        if token_path is None:
            print(f"[SKIP] {network}: token CSV non trovato (cercavo '{token_key}-usd-max.csv')")
            continue

        try:
            gas_median   = float(_load_gas(gas_path).median())
            token_median = float(_load_token(token_path).median())
            results[network] = (gas_median, token_median)
        except ValueError as e:
            print(f"[WARN] {e}")

    return results


if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser()
    parser.add_argument("dir", nargs="?", default=".", help="Directory con i CSV (default: .)")
    args = parser.parse_args()

    data = extract_all(args.dir)

    if not data:
        print("Nessun risultato.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'Network':<8}  {'gas_gwei (median)':>20}  {'token_usd (median)':>20}  {'usd_per_gas':>18}")
    print("-" * 74)
    for net, (g, t) in data.items():
        usd = g * 1e-9 * t
        print(f"{net:<8}  {g:>20.4f}  {t:>20.6f}  {usd:>18.10f}")

    print(f"\ndict completo:\n{data}")