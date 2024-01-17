def WithSubclasses(obj):
    """
    A special helper function to allow a class type to be passed and also allow all subclasses of that type.

    Requires:

    - `obj`:
        - What: An uninitialized class that should also be considered type correct if a subclass is passed.
        - Type: Any Uninitialized class

    Returns:

    - `out`:
        - What: A list of all of the subclasses (recursively parsed)
        - Type: list of strs


    Notes:

    - From a functional perspective, this recursively get the subclasses for an uninitialised class (type).
    """
    out = [obj]
    for i in obj.__subclasses__():
        out += WithSubclasses(i)
    return out
