def matches(ap, criteria):
    if ap["price"] is None or ap["rooms"] is None:
        return False

    if ap["expensas"] is None:
        return False  # conservative: ignore listings without expensas

    # Check minimum rooms
    if ap["rooms"] < criteria["min_rooms"]:
        return False

    # Check maximum rooms if specified
    if criteria.get("max_rooms") is not None and ap["rooms"] > criteria["max_rooms"]:
        return False

    return (
        ap["price"] <= criteria["max_price"]
        and ap["expensas"] <= criteria["max_expensas"]
    )
