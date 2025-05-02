import json
from typing import List, Optional

from fastapi import APIRouter, Query
from starlette.requests import Request
from starlette_admin.contrib.beanie import ModelView
from starlette_admin.contrib.beanie.converters import BeanieModelConverter


class FastAPIModelView(ModelView):
    def __init__(
        self,
        document: type,
        icon: str | None = None,
        name: str | None = None,
        label: str | None = None,
        identity: str | None = None,
        converter: BeanieModelConverter | None = None,
        prefix: str = "",
    ):
        super().__init__(document, icon, name, label, identity, converter)
        self.router = APIRouter(
            prefix=f"/{prefix}{self.identity}", tags=[self.identity]
        )

        self.router.add_api_route(
            "/edit", self.edit, methods=["PATCH"], response_model=self.document
        )
        self.router.add_api_route(
            "/create", self.create, methods=["POST"], response_model=self.document
        )
        self.router.add_api_route(
            "/delete", self.delete, methods=["DELETE"], response_model=Optional[int]
        )
        self.router.add_api_route(
            "/get",
            self.find_by_pk,
            methods=["GET"],
            response_model=Optional[self.document],
        )
        self.router.add_api_route(
            "/list", self.find_all, methods=["GET"], response_model=list[self.document]
        )

    async def find_all(
        self,
        request: Request,
        skip: int = Query(default=0),
        limit: int = Query(default=100),
        where: str = Query(""),
        order_by: List[str] = Query(["id asc"]),
    ):
        if where is None:
            where = ""

        try:
            where_json = json.loads(where)
            return await super().find_all(request, skip, limit, where_json, order_by)
        except json.JSONDecodeError:
            pass
        return await super().find_all(request, skip, limit, where, order_by)
