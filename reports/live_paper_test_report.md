# MEME ALPHA HUNTER - LIVE & PAPER EXECUTION VERIFICATION REPORT
- **System:** MEME ALPHA HUNTER (Autonomous Solana Memecoin Discovery, Intelligence & Sniper Platform)
- **Target Network:** Solana Mainnet
- **Execution Mode:** Benchmark Simulation & Paper Accounting Engine
- **Data Ingestion Mode:** `DATA_MODE=mock` (High-Fidelity Offline Benchmark Mode)
- **Real Live Ingestion State:** `REAL_DATA_ONLY = FALSE` (Standard Sandbox Isolation Test Profile; Live mode reports `LIVE DATA UNAVAILABLE` when network is offline)
- **Evaluation Date:** 2026-09-05 (Timezone: Africa/Algiers)
- **Initial Virtual Capital:** $100.00 USD
- **Final Virtual Equity:** $106.33 USD
- **Net Realized PnL:** $+5.88 USD
- **Net Unrealized PnL:** $+0.45 USD
- **Total Fees Paid:** $0.62 USD (DEX AMM + Solana Base + Priority Gas Fees)
- **Total Slippage Drag:** $0.76 USD (Quadratic Impact Model)
- **Max Drawdown:** 0.47%
- **Closed Trades:** 6
- **Sample Quality Classification:** `EARLY_PAPER_OBSERVATION (Small Sample)`

---

## 2. Mathematical Accounting Invariant Reconciliation
The Virtual Wallet accounting engine strictly enforces dual-invariant validation on every cycle:

| Metric | Measured Value | Theoretical Expected | Discrepancy | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Cash Balance** | $61.19 | — | — | PASS |
| **Open Positions Net Liquidation** | $45.14 | — | — | PASS |
| **Ending Equity (Cash + Net Liq)** | $106.33 | $106.33 | $0.00 | **SATISFIED** |
| **Ending Equity (Capital + PnL)** | $106.33 | $106.33 | $0.00 | **SATISFIED** |
| **Invariant Verification Code** | `INVARIANTS_SATISFIED` | `INVARIANTS_SATISFIED` | None | **VERIFIED** |

---

## 3. Top Scored Memecoin Candidates

| Mint | Symbol | Score | Alpha | Risk | Conf | Regime | Earlyness | Exec Score | Narrative |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ALPHAPre...` | **PREIGNITE** | 82.1 | 73.1 | 1.0 | 76.8 | `R3_EARLY_IGNITION` | 86.0 | 75.0 | Whale Dynamics |
| `FASTSurg...` | **FASTSURGE** | 80.5 | 72.6 | 1.0 | 61.2 | `R3_EARLY_IGNITION` | 92.5 | 75.0 | Whale Dynamics |
| `9BB6NFEc...` | **FARTCOIN** | 77.0 | 72.3 | 0.0 | 100.0 | `R3_EARLY_IGNITION` | 30.0 | 95.0 | AI Agents |
| `CzLSujWB...` | **GOAT** | 75.9 | 69.8 | 0.0 | 100.0 | `R2_ACCUMULATION` | 30.0 | 95.0 | AI Agents |
| `DezXAZ8z...` | **BONK** | 73.4 | 64.3 | 0.0 | 100.0 | `R2_ACCUMULATION` | 30.0 | 95.0 | Dog / Community |
| `EKpQGSJt...` | **WIF** | 73.3 | 64.1 | 0.0 | 100.0 | `R2_ACCUMULATION` | 30.0 | 95.0 | Dog / Community |
| `Dfh5DzRg...` | **PIPPIN** | 72.2 | 61.5 | 0.0 | 100.0 | `R2_ACCUMULATION` | 30.0 | 95.0 | General Meme |
| `6p6xgHyF...` | **TRUMP** | 71.2 | 59.2 | 0.0 | 100.0 | `R2_ACCUMULATION` | 30.0 | 95.0 | General Meme |

---

## 4. Security Engine Hard Rejections (Rug & Scam Elimination)
Tokens flagged and killed before reaching the scoring/sniper pipeline:

| Mint | Symbol | Security Score | Rug Prob | Reason for Hard Rejection |
| :--- | :--- | :--- | :--- | :--- |
| `BadRugHo...` | **HONEYSCAM** | 0.0/100 | 100.0% | Creator/Dev wallet holds 65.0% (> 15.0% limit; High dump risk); LP Lock is 0.0% (< 70.0% required; Dev can pull liquidity); Top 10 holders control 88.0% (> 65.0% limit); Freeze Authority is ACTIVE (Creator can freeze user accounts/honeypot); Mint Authority is ACTIVE (Creator can mint unlimited tokens); HONEYPOT DETECTED: Sell transactions fail on-chain |
| `WashTrad...` | **WASHFAKE** | 49.7/100 | 50.3% | WASH TRADING DETECTED: High artificial volume from single entity cluster; LP Lock is 40.0% (< 70.0% required; Dev can pull liquidity); Creator/Dev wallet holds 28.0% (> 15.0% limit; High dump risk); Top 10 holders control 72.0% (> 65.0% limit) |
| `ThinMint...` | **THINLIQ** | 75.0/100 | 25.0% | Liquidity $350 < $1,000 min; Creator/Dev wallet holds 45.0% (> 15.0% limit; High dump risk); Top 10 holders control 92.0% (> 65.0% limit); LP Lock is 10.0% (< 70.0% required; Dev can pull liquidity) |
| `BadRugHo...` | **HONEYSCAM** | 0.0/100 | 100.0% | Creator/Dev wallet holds 65.0% (> 15.0% limit; High dump risk); LP Lock is 0.0% (< 70.0% required; Dev can pull liquidity); Top 10 holders control 88.0% (> 65.0% limit); Freeze Authority is ACTIVE (Creator can freeze user accounts/honeypot); Mint Authority is ACTIVE (Creator can mint unlimited tokens); HONEYPOT DETECTED: Sell transactions fail on-chain |
| `WashTrad...` | **WASHFAKE** | 49.7/100 | 50.3% | WASH TRADING DETECTED: High artificial volume from single entity cluster; LP Lock is 40.0% (< 70.0% required; Dev can pull liquidity); Creator/Dev wallet holds 28.0% (> 15.0% limit; High dump risk); Top 10 holders control 72.0% (> 65.0% limit) |
| `ThinMint...` | **THINLIQ** | 75.0/100 | 25.0% | Liquidity $350 < $1,000 min; Creator/Dev wallet holds 45.0% (> 15.0% limit; High dump risk); Top 10 holders control 92.0% (> 65.0% limit); LP Lock is 10.0% (< 70.0% required; Dev can pull liquidity) |

---

## 5. Paper Trading Execution Journal

| Symbol | Entry Price | Fill Size | Slippage | Fees Paid | Exit Price | Net PnL | Return | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FASTSURGE** | $0.000121 | $5.10 | $0.0551 | $0.0574 | $0.000138 | **$+0.72** | +14.2% | `TAKE_PROFIT_TIER_1 (+15.3% target hit)` |
| **WIF** | $0.185346 | $9.07 | $0.0977 | $0.0788 | $0.212566 | **$+1.30** | +14.3% | `TAKE_PROFIT_TIER_1 (+15.2% target hit)` |
| **FARTCOIN** | $0.115272 | $9.64 | $0.1048 | $0.0824 | $0.134560 | **$+1.60** | +16.6% | `TAKE_PROFIT_TIER_1 (+17.4% target hit)` |
| **GOAT** | $0.018734 | $9.64 | $0.1044 | $0.0822 | $0.021733 | **$+1.51** | +15.6% | `TAKE_PROFIT_TIER_1 (+16.5% target hit)` |
| **PREIGNITE** | $0.000483 | $6.46 | $0.0611 | $0.0605 | $0.000426 | **$-0.79** | -12.2% | `STOP_LOSS_TRIGGERED (-11.3% <= -10.0%)` |
| **PREIGNITE** | $0.000445 | $10.39 | $0.1126 | $0.0860 | $0.000512 | **$+1.54** | +14.9% | `TAKE_PROFIT_TIER_1 (+15.6% target hit)` |

---

## 6. Performance Metrics & Monte Carlo Analysis

### Sample Metrics
- **Total Trades:** 6
- **Win Rate:** 83.3% (5 wins, 1 losses)
- **Profit Factor:** 8.44
- **Average Trade PnL:** $+0.98 USD
- **Sample Classification:** `EARLY_PAPER_OBSERVATION (Small Sample)`

### Monte Carlo Simulation (1,000 Iterations)
- **Status:** `INSUFFICIENT_SAMPLE (6/8 trades min)`
- **Trade Sample Size:** 6
- **Median Ending Equity (50 trades forward):** $100.00 USD
- **P10 Worst Case Equity:** $100.00 USD
- **P90 Best Case Equity:** $100.00 USD
- **Probability of Ruin (< 50% capital):** 0.0%
- **Statistical Note:** *INSUFFICIENT_SAMPLE (6/8 trades min). Statistical inferences will reach high statistical confidence once live continuous execution exceeds 30+ completed trades.*

---

## 7. Multi-Strategy Performance Allocation ($100 USD Base Each)

| Strategy Name | Target Regime | Win Rate | Trades | Max Drawdown | Total Return | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy A (Early Launch)** | $R_1, R_2, R_3$ | 100.0% | 1 | 0.0% | +5.6% | Active |
| **Strategy B (Smart Money)** | $R_3, R_4$ | 100.0% | 1 | 0.0% | +5.6% | Active |
| **Strategy C (Whale Momentum)** | $R_4, R_5$ | 0.0% | 0 | 0.0% | 0.0% | Standby |
| **Strategy D (Pre-Ignition)** | $R_2, R_3$ | 0.0% | 0 | 0.0% | 0.0% | Standby |
| **Strategy E (Hybrid Ensemble)** | $R_3, R_4, R_5$ | 100.0% | 2 | 0.0% | +5.6% | Active |

---

## 8. Exported Data Artifacts
All generated datasets are verified and saved in `reports/`:
- `reports/top_candidates.csv`: Full ranked token opportunities with intelligence vectors.
- `reports/trades.csv`: Detailed executed trade journal with MAE, MFE, slippage, and fee breakdowns.
- `reports/portfolio_history.csv`: Snapshot time series of cash, equity, drawdown, and PnL.
- `reports/rejected_tokens.csv`: Hard-rejected malicious tokens with security audit logs.
- `reports/whale_events.csv`: Detected whale accumulation and distribution transactions.
- `reports/signal_log.csv`: Regime shifts and opportunity score events.
- `reports/solmeme_live_run.db`: Full SQLite database snapshot.
