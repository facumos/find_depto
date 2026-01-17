from location_filter import filter_by_location


def matches(ap, criteria):
    if ap["price"] is None or ap["rooms"] is None:
        return False

    # Check minimum rooms
    if ap["rooms"] < criteria["min_rooms"]:
        return False

    # Check maximum rooms if specified
    if criteria.get("max_rooms") is not None and ap["rooms"] > criteria["max_rooms"]:
        return False

    # Check price range
    if criteria.get("min_price") is not None and ap["price"] < criteria["min_price"]:
        return False
    if ap["price"] > criteria["max_price"]:
        return False

    # Check expensas only if available
    if ap["expensas"] is not None and ap["expensas"] > criteria["max_expensas"]:
        return False

    # Check location (casco urbano) - include if unknown
    if not filter_by_location(ap, include_unknown=True):
        return False

    return True
