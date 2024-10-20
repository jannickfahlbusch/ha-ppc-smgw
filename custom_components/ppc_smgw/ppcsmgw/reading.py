from dataclasses import dataclass
from datetime import datetime

@dataclass
class Reading:
    value: str
    unit: str
    timestamp: datetime
    isvalid: str
    name: str
    obis: str
