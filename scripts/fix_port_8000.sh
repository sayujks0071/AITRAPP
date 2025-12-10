#!/bin/bash
# Kill any process using port 8000
PORT=8000
PID=$(lsof -ti:$PORT 2>/dev/null)

if [ -n "$PID" ]; then
    echo "🛑 Killing process $PID on port $PORT..."
    kill -9 $PID 2>/dev/null
    sleep 1
    if lsof -ti:$PORT >/dev/null 2>&1; then
        echo "⚠️  Process still running, trying force kill..."
        kill -9 $PID 2>/dev/null
    fi
    echo "✅ Port $PORT is now free"
else
    echo "✅ Port $PORT is already free"
fi


