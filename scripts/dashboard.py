import time
import datetime as dt
import sys
import os
import requests
import glob
import yaml
from collections import deque
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich import box

# API Configuration
API_URL = "http://localhost:8000"

# State Buffers
log_buffer = deque(maxlen=10)
metrics_cache = {}

def fetch_api_state():
    """Aggregates data from all Level 12 subsystems."""
    data = {
        "health": {"status": "OFFLINE", "mode": "UNKNOWN"},
        "state": {},
        "positions": [],
        "execution": {"attempts": 0, "saved_slippage_rs": 0.0},
        "risk": {},
        "reflex": {},
    }

    try:
        # 1. Health
        r = requests.get(f"{API_URL}/health", timeout=0.5)
        if r.status_code == 200:
            data["health"] = r.json()

        # 2. System State (comprehensive)
        r = requests.get(f"{API_URL}/state", timeout=0.5)
        if r.status_code == 200:
            data["state"] = r.json()

        # 3. Positions
        r = requests.get(f"{API_URL}/positions", timeout=0.5)
        if r.status_code == 200:
            pos_data = r.json()
            data["positions"] = pos_data.get("net", pos_data.get("positions", []))

        # 4. Execution Stats (Level 4)
        r = requests.get(f"{API_URL}/api/execution/stats", timeout=0.5)
        if r.status_code == 200:
            data["execution"] = r.json()

        # 5. Risk State
        r = requests.get(f"{API_URL}/risk", timeout=0.5)
        if r.status_code == 200:
            data["risk"] = r.json()

        # 6. Reflex Status
        r = requests.get(f"{API_URL}/reflex/status", timeout=0.5)
        if r.status_code == 200:
            data["reflex"] = r.json()

    except requests.exceptions.RequestException:
        pass

    return data

def read_logs():
    """Tails the latest logs for the feed panel."""
    log_files = glob.glob("logs/trading.log")
    if not log_files: return
    
    latest_file = max(log_files, key=os.path.getmtime)
    try:
        with open(latest_file, "r") as f:
            # Efficiently read last few lines
            f.seek(0, os.path.SEEK_END)
            fsize = f.tell()
            f.seek(max(fsize - 2000, 0), 0) 
            lines = f.readlines()
            for line in lines[-10:]:
                clean_line = line.strip()
                if clean_line and clean_line not in log_buffer:
                    log_buffer.append(clean_line)
    except: pass

def generate_layout(data) -> Layout:
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=10)
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    layout["left"].split(
        Layout(name="strategies", ratio=2),
        Layout(name="positions", ratio=1)
    )
    layout["right"].split(
        Layout(name="intelligence", size=8),
        Layout(name="risk", size=8),
        Layout(name="execution")
    )
    return layout

def render_header(data):
    mode = data["health"].get("mode", "OFFLINE")
    state = data.get("state", {})
    is_market_open = state.get("is_market_open", False)
    is_paused = state.get("is_paused", False)

    # Determine status color and text
    if mode == "LIVE" and is_market_open and not is_paused:
        status = "🟢 LIVE"
        color = "green"
    elif mode == "LIVE" and is_paused:
        status = "🟡 PAUSED"
        color = "yellow"
    elif mode == "LIVE" and not is_market_open:
        status = "🟠 CLOSED"
        color = "yellow"
    else:
        status = "🔴 OFFLINE"
        color = "red"

    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="right", ratio=1)

    # Show live parameters
    daily_pnl = state.get("daily_pnl", 0.0)
    trades_today = state.get("trades_today", 0)
    win_rate = state.get("win_rate", 0.0)

    grid.add_row(
        f"[bold white]AITRAPP LEVEL 12 COMMANDER[/bold white]",
        f"Mode: [bold {color}]{status}[/] | Market: [{'green' if is_market_open else 'red'}]{'OPEN' if is_market_open else 'CLOSED'}[/]",
        f"[bold cyan]{dt.datetime.now().strftime('%H:%M:%S')}[/bold cyan] | PnL: [{'green' if daily_pnl >= 0 else 'red'}]₹{daily_pnl:,.0f}[/] | Trades: {trades_today} | WR: {win_rate:.0%}"
    )
    return Panel(grid, style=color, box=box.ROUNDED)

def render_intelligence(data):
    # Level 5/7/8 Display
    state = data.get("state", {})
    reflex = data.get("reflex", {})
    risk = data.get("risk", {})

    # Get reflex status
    reflex_enabled = reflex.get("enabled", False)
    reflex_status = "🟢 ARMED" if reflex_enabled else "🔴 DISABLED"

    # Get connection status
    ws_connected = state.get("websocket_connected", False)
    md_connected = state.get("marketdata_connected", False)

    table = Table(show_header=False, box=None, expand=True)
    table.add_column("Module", style="cyan")
    table.add_column("Status", justify="right")

    table.add_row("🌐 Market Data", f"[{'green' if md_connected else 'red'}]{'Connected' if md_connected else 'Offline'}[/]")
    table.add_row("📡 WebSocket", f"[{'green' if ws_connected else 'red'}]{'Live' if ws_connected else 'Down'}[/]")
    table.add_row("⚡ Reflex (L10)", f"[bold {'green' if reflex_enabled else 'red'}]{reflex_status}[/]")

    # Add position count and risk metrics
    positions = state.get("positions_count", 0)
    table.add_row("📊 Positions", f"[bold white]{positions}[/]")

    return Panel(table, title="[bold blue]Intelligence Layer[/]", border_style="blue", box=box.ROUNDED)

def render_strategies(data):
    # Level 12 PME Display - Load from config
    table = Table(expand=True, box=None)
    table.add_column("Strategy", style="white", width=28)
    table.add_column("Pri", justify="center", width=4)
    table.add_column("Status", justify="center", width=8)

    try:
        with open("configs/kite_day1_live.yaml", "r") as f:
            config = yaml.safe_load(f)

        strategies = config.get("strategies", [])
        # Sort by priority
        strategies.sort(key=lambda x: x.get("priority", 99))

        for s in strategies[:8]:  # Show top 8 strategies
            name = s.get("name", "Unknown")
            # Shorten long names
            name = name.replace("expiry_short_strangle_v2", "ESS-V2")
            name = name.replace("intraday_short_strangle_v1", "ISS-V1")
            name = name.replace("trend_credit_spread_v1", "TCS-V1")
            name = name.replace("RegimeVolEngine", "R1-Regime")
            name = name.replace("GammaScalper", "G1-Gamma")
            name = name.replace("CalendarArb", "T1-Calendar")
            name = name.replace("DispersionArb", "D1-Dispersion")
            name = name.replace("TailShortVolOverlay", "H1-Tail")
            name = name.replace("OptionsRanker", "OR-Spreads")
            name = name.replace("expiry_short_strangle", "ESS")

            priority = s.get("priority", "-")
            enabled = s.get("enabled", False)
            status = "🟢" if enabled else "⚪"

            table.add_row(name, str(priority), status)

    except Exception as e:
        table.add_row("[dim]Config load error[/dim]", "-", "⚪")

    return Panel(table, title="[bold magenta]Strategy Suite (L12)[/]", border_style="magenta", box=box.ROUNDED)

def render_risk(data):
    # Display live risk parameters from config
    table = Table(show_header=False, box=None, expand=True)
    table.add_column("Parameter", style="yellow")
    table.add_column("Value", justify="right")

    try:
        with open("configs/kite_day1_live.yaml", "r") as f:
            config = yaml.safe_load(f)

        risk = config.get("risk", {})
        guards = config.get("guards", {})
        entry = config.get("entry", {})

        # Key risk parameters
        table.add_row("Trade Risk", f"{risk.get('per_trade_risk_pct', 0):.2f}%")
        table.add_row("Max Heat", f"{risk.get('max_portfolio_heat_pct', 0):.1f}%")
        table.add_row("Daily Stop", f"{risk.get('daily_loss_stop_pct', 0):.2f}%")
        table.add_row("Max Positions", f"{risk.get('max_positions', 0)}")
        table.add_row("─" * 20, "─" * 8)
        table.add_row("Entry Window", f"{entry.get('window_start', 'N/A')}-{entry.get('window_end', 'N/A')}")
        table.add_row("Max Entries/Day", f"{entry.get('max_entries_per_day', 0)}")
        table.add_row("Cooldown (min)", f"{entry.get('cooldown_minutes', 0)}")

    except Exception as e:
        table.add_row("[dim]Config load error[/dim]", "")

    return Panel(table, title="[bold yellow]Risk Parameters (L11)[/]", border_style="yellow", box=box.ROUNDED)

def render_execution(data):
    # Level 4 Limit Chase Stats
    exec_data = data.get("execution", {})
    attempts = exec_data.get("attempts", 0)
    savings = exec_data.get("saved_slippage_rs", 0.0)
    
    grid = Table.grid(expand=True)
    grid.add_row(f"Orders Processed: [bold]{attempts}[/]")
    grid.add_row(f"Alpha Generated:  [bold green]₹{savings:.2f}[/]")
    grid.add_row("")
    
    # Live Feed
    for log in list(log_buffer)[-6:]:
        color = "white"
        if "ERROR" in log: color = "red"
        elif "WARNING" in log: color = "yellow"
        elif "SUCCESS" in log or "Secured" in log: color = "green"
        elif "Limit Chase" in log: color = "cyan"
        
        # Truncate timestamp
        clean_msg = log[11:] if len(log) > 11 else log
        grid.add_row(f"[{color}]{clean_msg}[/]")

    return Panel(grid, title="[bold yellow]Execution Engine (L4)[/]", border_style="yellow", box=box.ROUNDED)

def render_positions(data):
    pos = data.get("positions", [])
    
    table = Table(expand=True, box=None, show_header=True)
    table.add_column("Symbol", style="dim")
    table.add_column("Qty")
    table.add_column("PnL", justify="right")
    
    if not pos:
        table.add_row("[dim]No Active Positions[/dim]", "", "")
    else:
        for p in pos:
            qty = p.get('quantity', 0)
            if qty == 0: continue
            pnl = float(p.get('pnl', 0))
            color = "green" if pnl >= 0 else "red"
            table.add_row(p['tradingsymbol'], str(qty), f"[{color}]{pnl:.2f}[/]")

    return Panel(table, title="[bold white]Live Positions[/]", border_style="white", box=box.ROUNDED)

def main():
    # Setup
    layout = generate_layout({})
    
    with Live(layout, refresh_per_second=2, screen=True) as live:
        while True:
            try:
                # 1. Fetch Data
                state = fetch_api_state()
                read_logs()
                
                # 2. Update Components
                layout["header"].update(render_header(state))
                layout["intelligence"].update(render_intelligence(state))
                layout["risk"].update(render_risk(state))
                layout["strategies"].update(render_strategies(state))
                layout["execution"].update(render_execution(state))
                layout["positions"].update(render_positions(state))
                layout["footer"].update(Panel(Text("Press Ctrl+C to Exit Mission Control", justify="center", style="dim"), box=box.MINIMAL))
                
            except KeyboardInterrupt:
                sys.exit(0)
            except Exception as e:
                layout["footer"].update(Panel(f"Error: {e}", style="red"))

if __name__ == "__main__":
    main()




