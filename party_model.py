

class Party:

    def __init__(self, name: str, delegates: int, anti: list, hash_val: int):
        self.hash = hash_val
        self.name = name
        self.delegates = delegates
        self.anti = anti
