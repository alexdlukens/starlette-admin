from enum import Enum
from typing import Optional, List

from beanie import Document, Link, BackLink
from pydantic import EmailStr, Field, HttpUrl, PastDate, BaseModel
from starlette.requests import Request

class Category(Enum):
    ELECTRONICS = "Electronics"
    FASHION = "Fashion"
    HOME = "Home"
    BEAUTY = "Beauty"


class Image(BaseModel):
    url: HttpUrl
    alt_text: Optional[str] = Field(default=None, min_length=3, max_length=100)


class Location(BaseModel):
    street: str = Field(min_length=3, max_length=100)
    city: str = Field(min_length=3, max_length=50)
    state: str = Field(min_length=2, max_length=50)
    zip_code: str = Field(min_length=5, max_length=10)
    image: Optional[Image] = None
    friendly_name: Optional[str] = Field(default=None, min_length=3, max_length=50)

class Product(Document):
    name: str = Field(min_length=3, max_length=100)
    description: str
    price: float
    category: Category
    stock: int = Field(ge=0)
    stores: List[BackLink["Store"]] = Field(
        default_factory=list, json_schema_extra={"original_field": "products"}
    )

    async def __admin_repr__(self, request: Request) -> str:
        return self.name

    async def __admin_select2_repr__(self, request: Request) -> str:
        return f"<span>{await self.__admin_repr__()}</span>"

class Store(Document):
    name: str = Field(min_length=3, max_length=100)
    location: HttpUrl
    physical_address: Location
    email: EmailStr
    products: list[Link[Product]] = Field(default_factory=list)
    manager: Optional[BackLink["Manager"]] = Field(default=None, json_schema_extra={"original_field": "store"})

    async def __admin_repr__(self, request: Request) -> str:
        return f"{self.name} ({self.physical_address.friendly_name})"

    async def __admin_select2_repr__(self, request: Request) -> str:
        return f"<span>{await self.__admin_repr__()}</span>"

class Manager(Document):
    first_name: str = Field(min_length=3, max_length=50)
    last_name: str = Field(min_length=3, max_length=50)
    email: EmailStr
    birth_date: PastDate
    store: Optional[Link[Store]]

    async def __admin_repr__(self, request: Request) -> str:
        return f"{self.first_name} {self.last_name}"
    
    async def __admin_select2_repr__(self, request: Request) -> str:
        return f"<span>{await self.__admin_repr__()}</span>"

Product.model_rebuild(force=True)
Store.model_rebuild(force=True)
Manager.model_rebuild(force=True)
