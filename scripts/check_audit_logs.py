#!/usr/bin/env python3
"""Check audit logs for Day-3"""
import sys
from datetime import datetime, date, timedelta
from packages.storage.database import get_db_session
from packages.storage.models import AuditLog

REPORT_DATE = date(2025, 11, 18)

def check_logs():
    day_start = datetime.combine(REPORT_DATE, datetime.min.time())
    day_end = datetime.combine(REPORT_DATE, datetime.max.time()) + timedelta(days=1)
    
    with get_db_session() as db:
        logs = db.query(AuditLog).filter(
            AuditLog.ts >= day_start,
            AuditLog.ts < day_end
        ).order_by(AuditLog.ts).all()
        
        print(f"Total audit logs for {REPORT_DATE}: {len(logs)}\n")
        
        by_level = {}
        by_category = {}
        for log in logs:
            by_level[log.level] = by_level.get(log.level, 0) + 1
            by_category[log.category] = by_category.get(log.category, 0) + 1
        
        print("By Level:")
        for level, count in sorted(by_level.items()):
            print(f"  {level}: {count}")
        
        print("\nBy Category:")
        for cat, count in sorted(by_category.items()):
            print(f"  {cat}: {count}")
        
        print("\nSample logs (first 20):")
        for log in logs[:20]:
            print(f"  {log.ts} [{log.level}] [{log.category}] {log.message[:80]}")

if __name__ == "__main__":
    check_logs()


