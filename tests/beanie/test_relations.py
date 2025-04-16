import datetime
import json
import os
from enum import Enum
from typing import Annotated, Any, Dict

import pytest_asyncio
from beanie import Document, Indexed, Link, init_beanie
from beanie.operators import In
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import Field
from requests import Request
from starlette.applications import Starlette
from starlette_admin.contrib.beanie import Admin, ModelView

from tests.beanie import MONGO_URL

MONGO_DATABASE = os.environ.get("MONGO_DATABASE", "testdb")


class Brand(str, Enum):
    APPLE = "Apple"
    SAMSUNG = "Samsung"
    OPPO = "OPPO"
    HUAWEI = "Huawei"
    INFINIX = "Infinix"


class Product(Document):
    title: Annotated[str, Indexed(unique=True)] = Field(min_length=3)
    description: str
    price: float = Field(ge=0)
    brand: Brand
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class Store(Document):
    name: str = Field(min_length=3)
    products: list[Link[Product]] = []


class User(Document):
    name: str = Field(min_length=3)
    store: Link[Store] | None = None


class ProductView(ModelView):
    async def before_create(
        self, request: Request, data: Dict[str, Any], obj: Any
    ) -> None:
        assert isinstance(obj, Product)
        assert obj.id is None

    async def after_create(self, request: Request, obj: Any) -> None:
        assert isinstance(obj, Product)
        assert obj.id is not None

    async def before_edit(
        self, request: Request, data: Dict[str, Any], obj: Any
    ) -> None:
        assert isinstance(obj, Product)
        assert obj.id is not None

    async def after_edit(self, request: Request, obj: Any) -> None:
        assert isinstance(obj, Product)
        assert obj.id is not None

    async def before_delete(self, request: Request, obj: Any) -> None:
        assert isinstance(obj, Product)
        assert obj.id is not None

    async def after_delete(self, request: Request, obj: Any) -> None:
        assert isinstance(obj, Product)
        assert obj.id is not None


class TestMongoBasic:

    @pytest_asyncio.fixture(loop_scope="function")
    async def admin(self):
        self.motor_client = AsyncIOMotorClient(host=MONGO_URL)
        await self.motor_client.drop_database(MONGO_DATABASE)
        await init_beanie(
            database=self.motor_client.get_database(MONGO_DATABASE),
            document_models=[Product, Store, User],
        )
        with open("./tests/data/products.json") as f:
            for product in json.load(f):
                await Product(**product).save()
        admin = Admin()
        admin.add_view(ModelView(Store))
        admin.add_view(
            ProductView(
                Product,
                exclude_fields_from_create=["created_at"],
                exclude_fields_from_edit=["created_at"],
            )
        )
        admin.add_view(ModelView(User))

        yield admin

        await self.motor_client.drop_database(MONGO_DATABASE)
        self.motor_client.close()

    @pytest_asyncio.fixture(loop_scope="function")
    async def app(self, admin):
        app = Starlette()
        admin.mount_to(app)
        return app

    @pytest_asyncio.fixture(loop_scope="function")
    async def client(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as c:
            yield c

    async def test_relationships_base(self, client):
        response = await client.post(
            "/admin/store/create",
            data={
                "name": "Jewelry store",
                "products": [
                    x.id
                    for x in (
                        await Product.find(
                            In(Product.title, ["IPhone 9", "Huawei P30"])
                        ).to_list()
                    )
                ],
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert await Store.count() == 1
        store = await Store.find(Store.name == "Jewelry store").first_or_none()
        product_items = [await Product.get(x.ref.id) for x in store.products]
        assert sorted(x.title for x in product_items) == [
            "Huawei P30",
            "IPhone 9",
        ]
        response = await client.post(
            "/admin/user/create",
            data={
                "name": "John",
                "store": store.id,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert await User.count() == 1
        user = await User.find(User.name == "John").first_or_none()
        user_store = await Store.get(user.store.ref.id)
        assert user_store.name == "Jewelry store"

    async def test_edit_relationships(self, client):
        response = await client.post(
            "/admin/store/create",
            data={
                "name": "Jewelry store",
                "products": [
                    x.id
                    for x in (
                        await Product.find(
                            In(Product.title, ["IPhone 9", "Huawei P30"])
                        ).to_list()
                    )
                ],
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert await Store.count() == 1
        store = await Store.find(Store.name == "Jewelry store").first_or_none()
        product_items = [await Product.get(x.ref.id) for x in store.products]
        assert sorted(x.title for x in product_items) == [
            "Huawei P30",
            "IPhone 9",
        ]
        response = await client.post(
            "/admin/user/create",
            data={
                "name": "John",
                "store": store.id,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert await User.count() == 1
        user = await User.find(User.name == "John").first_or_none()
        user_store = await Store.get(user.store.ref.id)
        assert user_store.name == "Jewelry store"

        # remove store from user
        response = await client.post(
            f"/admin/user/edit/{user.id}",
            data={
                "name": "John",
                "store": None,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        assert await User.count() == 1
        user = await User.find(User.name == "John").first_or_none()
        assert user.store is None

        # add store back to user
        response = await client.post(
            f"/admin/user/edit/{user.id}",
            data={
                "name": "John",
                "store": store.id,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        user = await User.find(User.name == "John").first_or_none()
        user_store = await Store.get(user.store.ref.id)
        assert user_store.name == "Jewelry store"

    async def test_edit_relationships_list(self, client):
        response = await client.post(
            "/admin/store/create",
            data={
                "name": "Jewelry store",
                "products": [
                    x.id
                    for x in (
                        await Product.find(
                            In(Product.title, ["IPhone 9", "Huawei P30"])
                        ).to_list()
                    )
                ],
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert await Store.count() == 1
        store = await Store.find(Store.name == "Jewelry store").first_or_none()
        product_items = [await Product.get(x.ref.id) for x in store.products]
        assert sorted(x.title for x in product_items) == [
            "Huawei P30",
            "IPhone 9",
        ]

        # remove IPhone 9 from store
        response = await client.post(
            f"/admin/store/edit/{store.id}",
            data={
                "name": "Jewelry store",
                "products": [x.id for x in product_items if x.title == "Huawei P30"],
            },
            follow_redirects=False,
        )

        assert response.status_code == 303, response.text
        store = await Store.find(Store.name == "Jewelry store").first_or_none()
        product_items = [await Product.get(x.ref.id) for x in store.products]
        assert [x.title for x in product_items] == ["Huawei P30"]

        # remove Huawei P30 from store
        response = await client.post(
            f"/admin/store/edit/{store.id}",
            data={
                "name": "Jewelry store",
                "products": [],
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        store = await Store.find(Store.name == "Jewelry store").first_or_none()
        assert store.products == []
