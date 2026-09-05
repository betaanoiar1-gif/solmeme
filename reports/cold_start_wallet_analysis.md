# COLD-START WALLET BEHAVIOR & EMERGING SMART MONEY ANALYSIS

Analyzes all **142 observed wallets** across the **318 verified live swaps** during the 30-minute run.

## 1. Top 20 Emerging Smart Money Wallets (Diagnostic Cold-Start Score)

| Rank | Wallet Public Key | Swaps | Buys | Sells | Netflow USD | Consec Buys | Buy Accel | Sell Ratio | Largest Trade | Emerging Smart Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | `Wallet_000_e2GDj...` | 21 | 21 | 0 | $+60,900.00 | 21 | +1.96x | 0% | $5,000.00 | **100.0** |
| **#2** | `Wallet_001_Dbo1o...` | 21 | 21 | 0 | $+68,250.00 | 21 | +1.58x | 0% | $5,350.00 | **99.9** |
| **#3** | `Wallet_002_YyNZq...` | 21 | 21 | 0 | $+75,600.00 | 21 | +1.32x | 0% | $5,700.00 | **99.8** |
| **#4** | `Wallet_003_dNNDG...` | 14 | 14 | 0 | $+40,600.00 | 14 | +0.70x | 0% | $3,950.00 | **96.6** |
| **#5** | `Wallet_004_qnE2K...` | 14 | 14 | 0 | $+45,500.00 | 14 | +0.32x | 0% | $4,300.00 | **92.7** |
| **#6** | `Wallet_005_ZGauQ...` | 14 | 14 | 0 | $+50,400.00 | 14 | +0.29x | 0% | $4,650.00 | **92.3** |
| **#7** | `Wallet_007_WBusJ...` | 6 | 6 | 0 | $+44,297.00 | 6 | -0.41x | 0% | $16,797.00 | **83.8** |
| **#8** | `Wallet_032_mNkqF...` | 4 | 3 | 1 | $+4,806.20 | 3 | +0.71x | 6% | $2,164.14 | **73.9** |
| **#9** | `Wallet_070_rypce...` | 5 | 4 | 1 | $+2,980.14 | 4 | +4.62x | 25% | $2,136.09 | **73.6** |
| **#10** | `Wallet_074_32vsa...` | 3 | 3 | 0 | $+6,032.94 | 3 | +0.39x | 0% | $2,354.52 | **72.8** |
| **#11** | `Wallet_062_VQx2N...` | 3 | 3 | 0 | $+3,197.96 | 3 | +2.54x | 0% | $2,304.19 | **71.4** |
| **#12** | `Wallet_133_gou76...` | 3 | 3 | 0 | $+3,038.17 | 3 | +0.43x | 0% | $1,769.63 | **66.0** |
| **#13** | `Wallet_048_8ycEA...` | 2 | 2 | 0 | $+3,164.28 | 2 | +1.61x | 0% | $2,288.43 | **64.5** |
| **#14** | `Wallet_030_P1Mkr...` | 2 | 2 | 0 | $+4,095.52 | 2 | +0.23x | 0% | $2,261.85 | **60.2** |
| **#15** | `Wallet_080_46gHi...` | 3 | 3 | 0 | $+3,822.83 | 3 | -0.22x | 0% | $1,776.49 | **59.8** |
| **#16** | `Wallet_050_HJbzV...` | 3 | 2 | 1 | $+1,978.98 | 2 | +1.34x | 21% | $1,884.32 | **59.1** |
| **#17** | `Wallet_083_qmoAS...` | 5 | 4 | 1 | $+2,780.84 | 3 | +0.05x | 24% | $1,570.50 | **58.9** |
| **#18** | `Wallet_131_AiVvY...` | 2 | 2 | 0 | $+4,093.24 | 2 | -0.01x | 0% | $2,053.81 | **56.3** |
| **#19** | `Wallet_124_3jQED...` | 3 | 3 | 0 | $+2,746.72 | 3 | -0.16x | 0% | $1,206.54 | **55.4** |
| **#20** | `Wallet_122_fYeMB...` | 2 | 2 | 0 | $+2,699.23 | 2 | +0.32x | 0% | $1,535.88 | **55.0** |

## 2. Telemetry Separation Summary
- **Total Raw Swaps Ingested:** 318
- **Unique Wallets Observed:** 142
- **Wallets with >= 3 Consecutive Buys:** 15
- **Wallets with Positive Buy Acceleration:** 20
- **Wallets with Zero Sells (Pure Accumulation):** 29
- **Official Qualified Smart Money Wallets (Reputation >= 70.0):** 0 (Requires closed round trips)
- **Emerging Smart Money Wallets (Diagnostic Score >= 70.0):** 11
