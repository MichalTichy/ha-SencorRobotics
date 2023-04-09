"""Helper functions."""
import json
import socket


def parse_value(value):
    """Parse json string from vacuum cleaner"""
    if isinstance(value, str):
        try:
            return parse_value(json.loads(value))
        except Exception:
            pass
        semi_values = value.split(";")
        if len(semi_values) > 1:
            return list(map(parse_value, semi_values))
        comma_values = value.split(",")
        if len(comma_values) > 1:
            return list(map(parse_value, comma_values))
        if value.replace(".", "", 1).isdigit():
            return int(value)
    if isinstance(value, dict):
        return {k: parse_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return list(map(parse_value, value))
    return value


def host_available(host: str, port: int) -> bool:
    """Check if the host is available on the specified port."""
    success = True
    sock = socket.socket()
    try:
        sock.connect((host, port))
    except Exception:
        success = False
    finally:
        sock.close()
    return success
