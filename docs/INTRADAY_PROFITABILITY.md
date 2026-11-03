# Intraday profitability screen

The scanner now separates three quantities:

- **Risk-budget quantity**: the maximum shares allowed by the configured loss budget after estimated Groww charges.
- **Minimum quantity to clear fees**: the smallest quantity whose modeled Target 1 gross move exceeds the estimated round-trip charges. It is not a recommendation to increase risk.
- **Modeled net at Target 1**: the expected arithmetic result after estimated Groww charges for the risk-budget quantity.

## Trade gate

An active candidate is eligible only when all three checks pass:

1. ADX(14) is at least 20. ADX is treated as trend-strength evidence, not as a standalone volatility measure.
2. ATR(14) on the 5-minute candles is at least the fee break-even move per share. This is the movement test that prevents low-range trades from being labelled profitable.
3. The modeled Target 1 net is positive after charges.

If any input is unavailable or the setup is not a candidate, the result is `WAIT`; the application does not substitute synthetic profitability.

These are deterministic screening rules, not a profit forecast. Slippage, latency, partial fills, spread, and changing broker charges can turn a positive model into a loss. Groww fee assumptions therefore remain explicitly labelled as estimates in the UI.
