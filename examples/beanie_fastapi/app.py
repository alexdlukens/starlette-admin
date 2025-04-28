from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.routing import Route
from starlette_admin.contrib.beanie import Admin
from starlette_admin.contrib.beanie.fastapi import FastAPIModelView
from contextlib import asynccontextmanager
from .dependencies import create_db_and_tables

admin = Admin()


@asynccontextmanager
async def setup_db(app: FastAPI):

    models = await create_db_and_tables()
    for model in models:
        view = FastAPIModelView(
            model, name=model.__name__, icon="database", prefix="crud/"
        )
        app.include_router(view.router, prefix="")
        admin.add_view(view)

    yield


app = FastAPI(
    routes=[
        Route(
            "/",
            lambda r: HTMLResponse('<a href="/admin/">Click me to get to Admin!</a>'),
        )
    ],
    lifespan=setup_db,
)
admin.mount_to(app)
