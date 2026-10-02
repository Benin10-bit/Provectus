"""Existing naive database timestamps are UTC; never rewrite historical timestamps."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os
TZ = ZoneInfo(os.getenv("STUDY_TIMEZONE", "America/Sao_Paulo"))

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def utc_naive(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value

def iso_utc(value):
    return utc_naive(value).replace(tzinfo=timezone.utc).isoformat() if value else None

def local_date(value):
    return utc_naive(value).replace(tzinfo=timezone.utc).astimezone(TZ).date()

def month_bounds(year, month):
    start = datetime(year, month, 1, tzinfo=TZ)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=TZ)
    return utc_naive(start), utc_naive(end)
