import json
from typing import Generic, List, Optional, Type, TypeVar

from beanie import Document, PydanticObjectId
from fastapi import APIRouter, Query
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette_admin.contrib.beanie import ModelView
from starlette_admin.contrib.beanie.converters import BeanieModelConverter

T = TypeVar("T", bound=Document)


class FastAPIModelView(ModelView, Generic[T]):
    def __init__(
        self,
        document: Type[T],
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
            "/one", self.find_one, methods=["GET"], response_model=Optional[document]
        )
        self.router.add_api_route(
            "/{pk}", self.edit, methods=["PATCH"], response_model=document
        )
        self.router.add_api_route(
            "/", self.create, methods=["POST"], response_model=document
        )
        self.router.add_api_route(
            "/{pk}", self.delete_route, methods=["DELETE"], response_model=Optional[int]
        )
        self.router.add_api_route(
            "/{pk}",
            self.find_by_pk,
            methods=["GET"],
            response_model=Optional[document],
        )
        self.router.add_api_route(
            "/", self.find_all_route, methods=["GET"], response_model=list[document]
        )

    async def find_one(self, request: Request, where: str = Query("")) -> Optional[T]:
        find_many_result = await self.find_all_route(
            request=request,
            where=where,
            skip=0,
            limit=2,
            order_by=["id asc"],
        )
        if find_many_result and len(find_many_result) > 1:
            raise ValueError("More than one result found, use find_all instead.")
        if not find_many_result:
            raise HTTPException(
                status_code=404,
                detail="No results found for the given query.",
            )
        return find_many_result[0]

    async def find_by_pk(
        self, request: Request, pk: PydanticObjectId, fetch_links: bool = Query(False)
    ):
        return await super().find_by_pk(request=request, pk=pk, fetch_links=fetch_links)

    async def delete_route(
        self, request: Request, pk: PydanticObjectId
    ) -> Optional[int]:
        return await super().delete(request=request, pks=[pk])

    async def find_all_route(
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
        except (json.JSONDecodeError, TypeError):
            pass
        return await super().find_all(request, skip, limit, where, order_by)
