# AITRAPP Paper Trading (systemd)

Use this unit to auto-restart the paper API on failure and run it via `scripts/start_paper_api.sh`.

1) Copy the unit:
```
sudo cp ops/systemd/aitrapp-paper.service /etc/systemd/system/
sudo systemctl daemon-reload
```
2) Enable and start:
```
sudo systemctl enable --now aitrapp-paper.service
```
3) Logs:
```
tail -f /Users/mac/CRYPTO/AITRAPP/logs/api_8000.log
```

Env defaults in the unit:
- `APP_MODE=PAPER`
- `APP_CONFIG=configs/kite_paper.yaml`
- `MOCK_KITE=0`

Adjust the `User`, `WorkingDirectory`, and env vars if you relocate the repo or want mock mode (`MOCK_KITE=1`).*** End Patch
