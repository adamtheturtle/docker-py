import os
from typing import Dict


def create_environment_dict(overrides: None) -> Dict[str, str]:
    """
    Create and return a copy of os.environ with the specified overrides
    """
    result = os.environ.copy()
    result.update(overrides or {})
    return result
