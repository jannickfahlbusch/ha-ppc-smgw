from dataclasses import dataclass

@dataclass
class Reading:
    value: str
    unit: str
    timestamp: str
    isvalid: str
    name: str
    obis: str
