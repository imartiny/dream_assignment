from abc import ABC, abstractmethod
from typing import List
from app.models import ProcessData

class Parser(ABC):
    @abstractmethod
    def parse(self, content: str) -> List[ProcessData]:
        pass