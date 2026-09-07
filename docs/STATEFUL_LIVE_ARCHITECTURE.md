# Stateful Live Architecture Baseline

This repository uses an incremental live-data model.

## Data plane
- DEX APIs provide current market state.
- Solana RPC provides on-chain verification and transaction evidence.
- Previously fetched transaction signatures are retained in bounded per-token state and are not fetched again during the same live run.
- UNKNOWN remains UNKNOWN; missing evidence is never converted into a positive safety claim.

## Market-state policy
- Live market reads use a short freshness window to avoid duplicate requests inside rapid cycles.
- When multiple Solana pairs exist, the execution candidate is selected using liquidity, with pair creation time as a tie-breaker.
- Discovery prioritizes recent market creation; liquidity is used for execution quality rather than replacing earlyness.

## Trading-state policy
- Paper entries require the canonical opportunity decision, evidence/confidence gating, anti-chase protection, verified liquidity, and token-level post-exit cooldown.
- Paper accounting remains independent from real-money execution.

## Validation objective
The next live validation is intended to measure whether the stateful architecture reduces redundant RPC/DEX work while preserving trustworthy evidence and stable paper-trading behavior. It is not a profitability claim and is not a live-money execution test.
