"""
Location filter for La Plata casco urbano.

The casco urbano of La Plata is bounded approximately by:
- Streets (calles): 1 to 31
- Avenues (avenidas): 32 to 72
- Diagonals: 73 to 80

This module parses addresses and determines if they fall within these bounds.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Casco urbano boundaries
CALLE_MIN = 1
CALLE_MAX = 31
AVENIDA_MIN = 32
AVENIDA_MAX = 72
DIAGONAL_MIN = 73
DIAGONAL_MAX = 80


def extract_street_numbers(address: str) -> list[int]:
    """
    Extract street/avenue numbers from an address string.

    Handles formats like:
    - "Calle 7 entre 45 y 46"
    - "45 e/ 7 y 8"
    - "Av. 44 N° 123"
    - "Diagonal 73"
    - "7 y 45"
    - "calle 7 n 456"

    Returns:
        list: List of street numbers found in the address
    """
    if not address:
        return []

    # Normalize the address
    addr_lower = address.lower()

    # Remove common words that might contain numbers we don't want
    addr_clean = addr_lower
    for word in ['piso', 'dto', 'depto', 'departamento', 'unidad', 'uf', 'pb', 'pa']:
        addr_clean = re.sub(rf'\b{word}\b\s*\d*', '', addr_clean)

    numbers = []

    # Pattern for "calle/av/avenida/diagonal + number"
    street_patterns = [
        r'(?:calle|c\.?)\s*(\d{1,2})\b',
        r'(?:avenida|av\.?)\s*(\d{1,2})\b',
        r'(?:diagonal|diag\.?)\s*(\d{1,2})\b',
    ]

    for pattern in street_patterns:
        matches = re.findall(pattern, addr_clean)
        for m in matches:
            try:
                num = int(m)
                if 1 <= num <= 80:  # Valid La Plata street range
                    numbers.append(num)
            except ValueError:
                pass

    # Pattern for standalone numbers that look like streets (1-80)
    # "45 e/ 7 y 8" or "7 y 45" or "entre 45 y 46"
    standalone_pattern = r'\b(\d{1,2})\b'
    standalone_matches = re.findall(standalone_pattern, addr_clean)

    for m in standalone_matches:
        try:
            num = int(m)
            # Only consider numbers in valid street range that aren't already found
            if 1 <= num <= 80 and num not in numbers:
                # Check context - should be near street-related words or other small numbers
                numbers.append(num)
        except ValueError:
            pass

    # Remove duplicates while preserving order
    seen = set()
    unique_numbers = []
    for n in numbers:
        if n not in seen:
            seen.add(n)
            unique_numbers.append(n)

    return unique_numbers


def is_in_casco_urbano(address: str) -> bool | None:
    """
    Check if an address is within La Plata's casco urbano.

    Args:
        address: The address string to check

    Returns:
        True: Address is definitely in casco urbano
        False: Address is definitely outside casco urbano
        None: Cannot determine (address unclear or no street numbers found)
    """
    if not address:
        return None

    addr_lower = address.lower()

    # Check for known areas outside casco urbano
    outside_areas = [
        'city bell', 'citybell', 'gonnet', 'gorina', 'hernandez', 'hernández',
        'villa elisa', 'ringuelet', 'tolosa', 'los hornos', 'san carlos',
        'altos de san lorenzo', 'villa elvira', 'melchor romero', 'abasto',
        'olmos', 'etcheverry', 'arturo segui', 'arturo seguí'
    ]

    for area in outside_areas:
        if area in addr_lower:
            logger.debug(f"Address '{address}' is in '{area}' - outside casco urbano")
            return False

    # Check for "casco urbano" or "centro" explicitly mentioned
    if 'casco urbano' in addr_lower or 'casco céntrico' in addr_lower:
        return True

    # Extract street numbers
    numbers = extract_street_numbers(address)

    if not numbers:
        logger.debug(f"No street numbers found in '{address}'")
        return None

    logger.debug(f"Found street numbers {numbers} in '{address}'")

    # Check if numbers fall within casco urbano bounds
    # We need at least one number that could be a valid casco urbano street
    valid_numbers = []
    for num in numbers:
        if CALLE_MIN <= num <= CALLE_MAX:
            valid_numbers.append(('calle', num))
        elif AVENIDA_MIN <= num <= AVENIDA_MAX:
            valid_numbers.append(('avenida', num))
        elif DIAGONAL_MIN <= num <= DIAGONAL_MAX:
            valid_numbers.append(('diagonal', num))

    if not valid_numbers:
        # Numbers found but none in valid casco urbano range
        logger.debug(f"Street numbers {numbers} not in casco urbano range")
        return False

    # If we have valid numbers, assume it's in casco urbano
    logger.debug(f"Address appears to be in casco urbano: {valid_numbers}")
    return True


def filter_by_location(listing: dict, include_unknown: bool = True) -> bool:
    """
    Filter a listing by location.

    Args:
        listing: The listing dictionary (must have 'address' key)
        include_unknown: If True, include listings where location can't be determined

    Returns:
        True if listing should be included, False otherwise
    """
    address = listing.get('address', '')

    result = is_in_casco_urbano(address)

    if result is None:
        # Can't determine location
        return include_unknown

    return result
