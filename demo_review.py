def parse_count(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0