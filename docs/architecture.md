# MEME ALPHA HUNTER — SYSTEM ARCHITECTURE

## 1. High-Level Pipeline Architecture

```text
+---------------------------------------------------------------------------------------------------+
|                                      DATA INGESTION LAYER                                         |
|  Solana Public RPC  |  DexScreener API  |  Pump.fun Bonding Curves  |  Raydium Pools / WebSockets |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                    TOKEN DISCOVERY & DNA ENGINE                                   |
|  - Continuous scanning of new mints & active pools                                                |
|  - Time-series Token DNA tracking (Price, Volume, Liquidity, Holder dynamics)                      |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                 SECURITY & RUG DETECTION ENGINE                                   |
|  - Mint & Freeze Authority Checkers (Token-2022 extensions)                                       |
|  - Liquidity Lock & Burn Status                                                                   |
|  - Top-10 & Dev Wallet Concentration Filters                                                      |
|  - Honeypot & Wash-Trading Cluster Detectors                                                      |
|  => Calculates Security Score (0-100) & Rug Probability (0-100) -> Issues HARD REJECTs            |
+-------------------------------------------------+-------------------------------------------------+
                                                  | (Only SAFE/Qualified tokens pass)
                                                  v
+---------------------------------------------------------------------------------------------------+
|                              ON-CHAIN INTELLIGENCE & MICROSTRUCTURE                               |
|  - Whale Radar (Detects WHALE_BUY, WHALE_SELL, ACCUMULATION, DISTRIBUTION)                        |
|  - Smart Money Engine (Calculates Quality x Timing x Historical Win-Rate)                         |
|  - Wallet Cluster Graph (Discovers shared funding & cluster-discounted signals)                   |
|  - Market Microstructure (1st & 2nd order accelerations, Pre-Ignition & Divergence triggers)       |
|  - Narrative Engine (NLP / keyword theme clustering, Heat & Velocity)                             |
|  - Market Regime Engine (R0 DEAD to R9 COLLAPSE)                                                  |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                 MULTI-FACTOR SCORING & RANKING                                    |
|  - Alpha Score (0-100)                                                                            |
|  - Risk Score (0-100)                                                                             |
|  - Confidence Score (0-100)                                                                       |
|  - Earlyness Score (0-100) & Execution Score (0-100)                                              |
|  => Final Opportunity Score & Explainability Thesis Generation                                    |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                         SNIPER ENGINE                                             |
|  - Mode A: Early Launch Sniper                                                                    |
|  - Mode B: Smart Money Follow Sniper                                                              |
|  - Mode C: Whale Radar Sniper                                                                     |
|  - Mode D: Momentum & Pre-Ignition Sniper                                                         |
|  - Mode E: Hybrid AI Multi-Factor Sniper                                                          |
|  - Anti-Sniper Defense & Chase Detector (Token Quality vs Entry Quality)                           |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                              SIMULATED EXECUTION & VIRTUAL WALLET                                 |
|  - $100.00 USD Virtual Capital (Zero Real Money / Zero Private Keys)                              |
|  - Dynamic Position Sizing (Alpha, Risk, Liquidity cap)                                           |
|  - Execution Simulator (DEX LP Fees, Solana base & priority fees, AMM constant product slippage,  |
|    partial fills, latency simulation 250ms - 10s)                                                 |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                    DYNAMIC POSITION MONITORING                                    |
|  - Mark-to-market continuous valuation & Drawdown tracking                                        |
|  - Multi-tier Take Profits (+15%, +35%, +75%)                                                     |
|  - Stop Loss (-10%) & Trailing Stops (Activates +12%, trails 5% below peak)                       |
|  - Smart Money Dump Exits & Regime Breakdown Exits                                                |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                 ACCOUNTING, JOURNALING & ML LEARNING                              |
|  - Granular Trade Journal (Records MAE, MFE, latency, durations, signal state)                    |
|  - Multi-Strategy Portfolios (Conservative, Balanced, Aggressive, Smart Money, Hybrid AI)         |
|  - Probabilistic ML Model & Monte Carlo Path Simulation                                           |
|  - Automated Report & CSV Exporters in reports/                                                   |
+---------------------------------------------------------------------------------------------------+
```

## 2. Market Regime Lifecycle ($R_0 \to R_9$)

1. **`R0_DEAD`**: Zero volume, inactive pool.
2. **`R1_DORMANT`**: Low volume, flat liquidity.
3. **`R2_ACCUMULATION`**: Stealth Smart Money buying, price stable, low retail chatter.
4. **`R3_EARLY_IGNITION`**: Buyer acceleration surging, expanding liquidity, pre-ignition signature.
5. **`R4_CONFIRMED_IGNITION`**: Volume breakout confirmed, order flow imbalance > +0.30.
6. **`R5_EXPANSION`**: Broad retail inflow, higher highs, deepening liquidity.
7. **`R6_PARABOLIC`**: Extreme price slope, high velocity (> +30%).
8. **`R7_EUPHORIA`**: Retail chasing tops, Smart Money begins stealth distribution.
9. **`R8_DISTRIBUTION`**: Whale net selling, smart money netflow negative.
10. **`R9_COLLAPSE`**: Liquidity drain, panic selling, fake breakout breakdown.
