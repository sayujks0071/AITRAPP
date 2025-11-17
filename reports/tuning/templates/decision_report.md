# ORB – NIFTY Walk-Forward Decision

**Windowing:** IS {{is_days}} / OOS {{oos_days}} / stride {{stride_days}}  
**Trials:** {{trials}} sampled from {{grid_size}}  
**Costs:** {{cost_model_name}} | Slippage stress: +{{slip_lo}} → +{{slip_hi}} bps

## Summary

- OOS Sharpe (deflated): **{{sharpe}}**
- MAR: **{{mar}}**
- Win rate: **{{hit_rate}}%**
- Avg win / loss: **{{avgw}} / {{avgl}}**
- PBO: **{{pbo}}**

## Robust Params (Apply if GO)

```yaml
orb:
  session_or: "15m"
  atr_len: {{atr_len}}
  atr_mult: {{atr_mult}}
  confirm_candles: {{confirm_candles}}
  vol_z: {{vol_z}}
  widen_n: {{widen_n}}
  cool_down: {{cool_down}}
```

## Stress Summary

|         Slippage | OOS Sharpe | MAR | Notes |
| ---------------: | ---------: | --: | ----- |
| {{stress_table}} |            |     |       |

**GO / NO-GO:** {{decision}}


