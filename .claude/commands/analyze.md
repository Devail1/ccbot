# Trading Performance Analysis

Analyze live trading performance by querying the EC2 SQLite database.

## Period

The user's requested period: **$ARGUMENTS**

If the period is empty or unclear, use `AskUserQuestion` to ask:
- Options: "4h" (Last 4 hours), "8h" (Last 8 hours), "1d" (Last 24 hours), "3d" (Last 3 days), "7d" (Last 7 days), "30d" (Last 30 days), "all" (All time)

## Period Mapping

Convert the user's period to a SQLite datetime modifier:
| Input | SQL modifier |
|-------|-------------|
| 4h | -4 hours |
| 8h | -8 hours |
| 1d | -1 days |
| 3d | -3 days |
| 7d / 1w | -7 days |
| 30d | -30 days |
| all | no WHERE clause on time |

## How to Query

Run queries via SSH. Use `sqlite3 -json` for parseable output:

```bash
ssh my-ec2-instance "sqlite3 -json ~/python-agent/v5/account_data.db '<SQL>'"
```

**Account IDs:** `trend_mainnet` (basic_trend_v1) and `breakout_mainnet` (breakout_v1).

Replace `<PERIOD>` below with the appropriate SQLite datetime modifier (e.g., `-7 days`).

## Queries to Run

Run these queries in parallel where possible:

### 1. Strategy Performance Summary (closed trades in period)

```sql
SELECT
  account_id,
  strategy,
  COUNT(*) as trades,
  SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
  ROUND(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate,
  ROUND(SUM(pnl), 2) as total_pnl,
  ROUND(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END), 2) as gross_profit,
  ROUND(SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END), 2) as gross_loss,
  ROUND(
    CASE WHEN SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) > 0
    THEN SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) / SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END)
    ELSE 999 END, 2) as profit_factor,
  ROUND(AVG(pnl), 2) as avg_pnl
FROM trades
WHERE status = 'closed'
  AND entry_time >= datetime('now', '<PERIOD>')
GROUP BY account_id, strategy
ORDER BY total_pnl DESC;
```

### 2. Close Reason Breakdown

```sql
SELECT
  strategy,
  SUM(CASE WHEN reason LIKE '%Trailing Stop%' OR reason LIKE '%TSL%' THEN 1 ELSE 0 END) as tsl_closes,
  SUM(CASE WHEN reason LIKE '%Stop Loss%' OR reason LIKE '%SL%' THEN 1 ELSE 0 END) as sl_closes,
  SUM(CASE WHEN reason LIKE '%active_exit%' OR reason LIKE '%regime%' THEN 1 ELSE 0 END) as active_exit_closes,
  SUM(CASE WHEN reason NOT LIKE '%Trailing Stop%' AND reason NOT LIKE '%TSL%' AND reason NOT LIKE '%Stop Loss%' AND reason NOT LIKE '%SL%' AND reason NOT LIKE '%active_exit%' AND reason NOT LIKE '%regime%' THEN 1 ELSE 0 END) as other_closes
FROM trades
WHERE status = 'closed'
  AND entry_time >= datetime('now', '<PERIOD>')
GROUP BY strategy;
```

### 3. Top 5 Winners and Losers

```sql
SELECT symbol, strategy, side, ROUND(pnl, 2) as pnl, ROUND(pnl_pct, 2) as pnl_pct, entry_time, exit_time
FROM trades
WHERE status = 'closed' AND entry_time >= datetime('now', '<PERIOD>')
ORDER BY pnl DESC LIMIT 5;
```

```sql
SELECT symbol, strategy, side, ROUND(pnl, 2) as pnl, ROUND(pnl_pct, 2) as pnl_pct, entry_time, exit_time
FROM trades
WHERE status = 'closed' AND entry_time >= datetime('now', '<PERIOD>')
ORDER BY pnl ASC LIMIT 5;
```

### 4. Current Open Positions

```sql
SELECT account_id, symbol, strategy, side, ROUND(entry_price, 4) as entry, ROUND(pnl, 2) as unrealized_pnl, entry_time
FROM trades
WHERE status = 'open'
ORDER BY entry_time DESC;
```

### 5. Latest Wallet Balances

```sql
SELECT account_id, ROUND(wallet_balance, 2) as balance, ROUND(unrealized_pnl, 2) as unrealized, snapshot_time
FROM balance_snapshots
WHERE id IN (
  SELECT MAX(id) FROM balance_snapshots GROUP BY account_id
);
```

## Output Format

Present the results as a clean markdown summary:

```
## Trading Performance — [period description]

### Account Balances
- v5-trend (trend_mainnet): $XXX
- v5-breakout (breakout_mainnet): $XXX

### Strategy Performance
| Strategy | Trades | Win% | PnL | PF | Avg Trade |
|----------|--------|------|-----|----|-----------|
| ... | ... | ... | ... | ... | ... |

### Close Reasons
| Strategy | TSL | SL | Active Exit | Other |
|----------|-----|----|-------------|-------|
| ... | ... | ... | ... | ... |

### Top Winners
1. SYMBOL SIDE +$X.XX (+X.XX%) — strategy
...

### Top Losers
1. SYMBOL SIDE -$X.XX (-X.XX%) — strategy
...

### Open Positions (X total)
- SYMBOL SIDE @ entry — unrealized $X.XX (strategy)
...

### Key Insights
- [Brief observations about performance, trends, notable patterns]
```

Keep insights concise and actionable. Flag any concerning metrics (win rate below 30%, negative PF, large drawdowns).
