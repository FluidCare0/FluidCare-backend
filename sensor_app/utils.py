import logging
from datetime import datetime, timezone as dt_timezone

mqtt_logger = logging.getLogger('mqtt')
django_logger = logging.getLogger('django')


def parse_datetime(datetime_str):
    """
    Parse multiple datetime formats safely for IoT payloads.
    Handles both backend and device formats.
    """
    possible_formats = [
        "%Y-%m-%d %H:%M:%S",        # Device format
        "%b. %d, %Y, %I:%M:%S %p",  # Backend format
        "%b %d, %Y, %I:%M:%S %p",   # Variant (no dot)
        "%Y-%m-%dT%H:%M:%S",        # ISO fallback
    ]

    for fmt in possible_formats:
        try:
            parsed = datetime.strptime(datetime_str, fmt)
            if fmt != possible_formats[0]:
                mqtt_logger.warning(f"⚠️ Parsed datetime with fallback format '{fmt}': {datetime_str}")
            return parsed
        except ValueError:
            continue

    raise ValueError(f"Unsupported datetime format: {datetime_str}")