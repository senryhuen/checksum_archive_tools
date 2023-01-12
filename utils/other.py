"""Miscellaneous Utilities 

Contains the following functions:
    * index_if_possible

"""


def index_if_possible(array: list, search_item) -> int:
    """
    Args:
        array (list): List to be searched for `search_item`.
        search_item (any): Item to search for in `array`.

    Returns:
        int: index of first occurrence of `search_item` in `array`, or -1 if
            `search_item` does not occur in `array`

    """
    try:
        idx = array.index(search_item)
    except ValueError:
        idx = -1

    return idx
