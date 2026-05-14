import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

USE_BRIGHTDATA: bool = os.getenv("USE_BRIGHTDATA", "false").lower() == "true"
BRIGHTDATA_API_TOKEN: str = os.getenv("BRIGHTDATA_API_TOKEN", "")

_BASE_URL = "https://www.domain.com.au/sale/"

_SUBURBS = [
    "bulleen-vic-3105",
    "templestowe-lower-vic-3107",
    "doncaster-vic-3108",
    "doncaster-east-vic-3109",
    "donvale-vic-3111",
    "mont-albert-vic-3127",
    "mont-albert-north-vic-3129",
    "box-hill-vic-3128",
    "box-hill-north-vic-3129",
    "box-hill-south-vic-3128",
    "blackburn-vic-3130",
    "blackburn-north-vic-3130",
    "blackburn-south-vic-3130",
    "burwood-vic-3125",
    "mount-waverley-vic-3149",
    "balwyn-vic-3103",
    "balwyn-north-vic-3104",
    "surrey-hills-vic-3127",
    "deepdene-vic-3103",
    "camberwell-vic-3124",
]


@dataclass
class SearchConfig:
    suburbs: list[str] = field(default_factory=lambda: list(_SUBURBS))
    min_beds: int = 3
    min_baths: int = 2
    max_price: int = 1_600_000
    property_type: str = "house"

    def search_url(self, page: int) -> str:
        return (
            f"{_BASE_URL}?suburb={','.join(self.suburbs)}"
            f"&bedrooms={self.min_beds}-any"
            f"&bathrooms={self.min_baths}-any"
            f"&price=0-{self.max_price}"
            f"&ptype={self.property_type}"
            f"&page={page}"
        )


DEFAULT_CONFIG = SearchConfig()
