from typing import Any, Dict

class DictType(dict):
    def __init__(self, init: Dict[str, Any]) -> None:
        for k, v in init.items():
            self[k] = v
