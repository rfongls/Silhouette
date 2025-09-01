from abc import ABC, abstractmethod
from typing import Iterable, Dict

class BaseAdapter(ABC):
    """
    Dataset adapters must yield dicts of the form:
      {'instruction': str, 'input': str, 'output': str, 'tools_used': list | None}
    Domain-agnostic by design.
    """
    @abstractmethod
    def samples(self) -> Iterable[Dict]:
        ...
