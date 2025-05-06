from starlette_admin.contrib.beanie.fastapi import FastAPIModelView as ModelView


class ProductView(ModelView):
    fetch_links_in_list = True
    handle_backlinks_in_list = True


class StoreView(ModelView):
    fetch_links_in_list = True
    handle_backlinks_in_list = True


class ManagerView(ModelView):
    fetch_links_in_list = True
    handle_backlinks_in_list = True
