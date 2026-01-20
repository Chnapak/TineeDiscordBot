import re
from datetime import timedelta


def format_timedelta(delta):
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def parse_duration(text):
    if not text:
        return None
    value = text.strip().lower()
    if value.isdigit():
        return int(value) * 60
    matches = re.findall(r"(\d+)\s*([smhd])", value)
    if not matches:
        return None
    total = 0
    for amount, unit in matches:
        amount_int = int(amount)
        if unit == "s":
            total += amount_int
        elif unit == "m":
            total += amount_int * 60
        elif unit == "h":
            total += amount_int * 3600
        elif unit == "d":
            total += amount_int * 86400
    remainder = re.sub(r"(\d+)\s*[smhd]", "", value).strip()
    if remainder:
        return None
    return total


def build_track_link(url):
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://www.youtube.com/watch?v={url}"


def format_seconds(seconds):
    return format_timedelta(timedelta(seconds=seconds))
