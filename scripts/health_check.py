#!/usr/bin/env python3
"""
AITRAPP Infrastructure Startup & Health Check
==============================================

Verifies system health and infrastructure status.
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import requests


def check_docker() -> Dict[str, Any]:
    """Check Docker daemon and services"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return {"status": "error", "message": "Docker daemon not running"}
        
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    container = json.loads(line)
                    containers.append({
                        "name": container.get("Names", ""),
                        "status": container.get("Status", ""),
                        "ports": container.get("Ports", "")
                    })
                except:
                    pass
        
        # Check for AITRAPP services
        postgres = any("postgres" in c["name"].lower() for c in containers)
        redis = any("redis" in c["name"].lower() for c in containers)
        
        return {
            "status": "running",
            "containers": containers,
            "postgres_running": postgres,
            "redis_running": redis
        }
    except FileNotFoundError:
        return {"status": "error", "message": "Docker not installed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity"""
    try:
        result = subprocess.run(
            ["redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and "PONG" in result.stdout:
            return {"status": "healthy", "port": 6379}
        return {"status": "unreachable"}
    except FileNotFoundError:
        # Try via Docker
        try:
            result = subprocess.run(
                ["docker", "exec", "aitrapp-redis-1", "redis-cli", "ping"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and "PONG" in result.stdout:
                return {"status": "healthy", "port": 6379, "via": "docker"}
        except:
            pass
        return {"status": "unreachable", "message": "Redis CLI not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_postgres() -> Dict[str, Any]:
    """Check Postgres connectivity"""
    try:
        result = subprocess.run(
            ["docker", "exec", "aitrapp-postgres-1", "pg_isready", "-U", "trader"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return {"status": "healthy", "port": 5432, "via": "docker"}
    except:
        pass
    
    # Try direct connection
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="trader",
            password="trader",
            database="aitrapp",
            connect_timeout=2
        )
        conn.close()
        return {"status": "healthy", "port": 5432}
    except ImportError:
        return {"status": "unknown", "message": "psycopg2 not installed"}
    except Exception as e:
        return {"status": "unreachable", "message": str(e)}


def check_api() -> Dict[str, Any]:
    """Check API health endpoints"""
    base_url = "http://localhost:8000"
    results = {}
    
    try:
        # Health endpoint
        resp = requests.get(f"{base_url}/health", timeout=2)
        if resp.status_code == 200:
            results["health"] = resp.json()
        else:
            results["health"] = {"status": "error", "code": resp.status_code}
    except Exception as e:
        results["health"] = {"status": "unreachable", "error": str(e)}
    
    try:
        # Ready endpoint
        resp = requests.get(f"{base_url}/ready", timeout=2)
        if resp.status_code == 200:
            results["ready"] = resp.json()
        else:
            results["ready"] = {"status": "error", "code": resp.status_code}
    except Exception as e:
        results["ready"] = {"status": "unreachable", "error": str(e)}
    
    try:
        # State endpoint
        resp = requests.get(f"{base_url}/state", timeout=2)
        if resp.status_code == 200:
            results["state"] = resp.json()
        else:
            results["state"] = {"status": "error", "code": resp.status_code}
    except Exception as e:
        results["state"] = {"status": "unreachable", "error": str(e)}
    
    return results


def check_python_version() -> Dict[str, Any]:
    """Check Python version compatibility"""
    import sys
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    compatible = sys.version_info >= (3, 9)
    
    return {
        "version": version,
        "compatible": compatible,
        "major": sys.version_info.major,
        "minor": sys.version_info.minor
    }


def main():
    """Run comprehensive health check"""
    print("=" * 60)
    print("AITRAPP Infrastructure Startup & Health Check")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # Check Python
    print("🐍 Python Version Check")
    python_info = check_python_version()
    print(f"   Version: {python_info['version']}")
    print(f"   Compatible: {'✅' if python_info['compatible'] else '❌'}")
    print()
    
    # Check Docker
    print("🐳 Docker Services Check")
    docker_info = check_docker()
    if docker_info["status"] == "running":
        print(f"   Status: ✅ Running")
        print(f"   Postgres: {'✅' if docker_info.get('postgres_running') else '❌'}")
        print(f"   Redis: {'✅' if docker_info.get('redis_running') else '❌'}")
        if docker_info.get("containers"):
            for container in docker_info["containers"]:
                print(f"   - {container['name']}: {container['status']}")
    else:
        print(f"   Status: ❌ {docker_info.get('message', 'Unknown error')}")
    print()
    
    # Check Redis
    print("📦 Redis Check")
    redis_info = check_redis()
    if redis_info["status"] == "healthy":
        print(f"   Status: ✅ Healthy")
        print(f"   Port: {redis_info.get('port', 'N/A')}")
        if redis_info.get("via"):
            print(f"   Via: {redis_info['via']}")
    else:
        print(f"   Status: ❌ {redis_info.get('message', 'Unreachable')}")
    print()
    
    # Check Postgres
    print("🐘 Postgres Check")
    postgres_info = check_postgres()
    if postgres_info["status"] == "healthy":
        print(f"   Status: ✅ Healthy")
        print(f"   Port: {postgres_info.get('port', 'N/A')}")
        if postgres_info.get("via"):
            print(f"   Via: {postgres_info['via']}")
    else:
        print(f"   Status: ❌ {postgres_info.get('message', 'Unreachable')}")
    print()
    
    # Check API
    print("🚀 API Health Check")
    api_info = check_api()
    
    if "health" in api_info and api_info["health"].get("status") == "healthy":
        health = api_info["health"]
        print(f"   /health: ✅ {health.get('status', 'unknown')}")
        print(f"   Mode: {health.get('mode', 'N/A')}")
        print(f"   Paused: {health.get('is_paused', 'N/A')}")
    else:
        print(f"   /health: ❌ Unreachable")
    
    if "ready" in api_info and api_info["ready"].get("status") == "ready":
        ready = api_info["ready"]
        print(f"   /ready: ✅ {ready.get('status', 'unknown')}")
        print(f"   Leader: {ready.get('leader', 'N/A')}")
        print(f"   Market Data Heartbeat: {ready.get('marketdata_heartbeat', 'N/A'):.2f}s")
        print(f"   Order Stream Heartbeat: {ready.get('order_stream_heartbeat', 'N/A'):.2f}s")
        print(f"   Scan Heartbeat: {ready.get('scan_heartbeat', 'N/A'):.2f}s")
    else:
        print(f"   /ready: ❌ Unreachable")
    
    if "state" in api_info and "timestamp" in api_info["state"]:
        state = api_info["state"]
        print(f"   /state: ✅ Active")
        print(f"   Mode: {state.get('mode', 'N/A')}")
        print(f"   Market Open: {state.get('is_market_open', 'N/A')}")
        print(f"   Positions: {state.get('positions_count', 0)}")
        print(f"   Trades Today: {state.get('trades_today', 0)}")
    else:
        print(f"   /state: ❌ Unreachable")
    print()
    
    # Summary
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    all_healthy = (
        docker_info.get("status") == "running" and
        redis_info.get("status") == "healthy" and
        postgres_info.get("status") == "healthy" and
        api_info.get("health", {}).get("status") == "healthy"
    )
    
    if all_healthy:
        print("✅ All systems operational")
    else:
        print("⚠️  Some systems may need attention")
        print()
        print("Next steps:")
        if docker_info.get("status") != "running":
            print("  - Start Docker: make up-infra")
        if redis_info.get("status") != "healthy":
            print("  - Check Redis: docker ps | grep redis")
        if postgres_info.get("status") != "healthy":
            print("  - Check Postgres: docker ps | grep postgres")
        if api_info.get("health", {}).get("status") != "healthy":
            print("  - Start API: make paper (or make live)")
    
    print()


if __name__ == "__main__":
    main()


