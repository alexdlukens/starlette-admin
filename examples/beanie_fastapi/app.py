from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.routing import Route
from starlette_admin.contrib.beanie import Admin
from contextlib import asynccontextmanager
from .dependencies import create_db_and_tables
from .views import ProductView, StoreView, ManagerView
admin = Admin()


@asynccontextmanager
async def setup_db(app: FastAPI):

    models = await create_db_and_tables()
    
    for model in models:
        if model.__name__ == "Store":
            view = StoreView(model, name=model.__name__, icon="database")
        elif model.__name__ == "Manager":
            view = ManagerView(model, name=model.__name__, icon="database")
        elif model.__name__ == "Product":
            view = ProductView(model, name=model.__name__, icon="database")
        else:
            raise ValueError(f"Unknown model: {model.__name__}")
        app.include_router(view.router, prefix="/crud")
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
