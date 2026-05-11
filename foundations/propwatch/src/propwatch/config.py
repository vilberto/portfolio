from dataclasses import dataclass


@dataclass
class SearchConfig:
    suburbs: list[str]
    min_beds: int
    min_baths: int
    max_price: int
    property_type: str


# TODO: initialise from env or a config file
DEFAULT_CONFIG: SearchConfig = ...
