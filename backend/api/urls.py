from django.urls import path

from ninja import NinjaAPI


api = NinjaAPI(
    title="PrintingPress",
)


from .views.count import router as count_router

api.add_router("count/", count_router)

from .views.charge import router as add_router

api.add_router("add/", add_router)

from .views.user.login import router as login_router
from .views.user.logout import router as logout_router

api.add_router("user/", login_router)
api.add_router("user/", logout_router)

from .views.admin.charge import router as admin_add_router
from .views.admin.deposit import router as admin_deposit_router

api.add_router("admin/deposit/", admin_deposit_router)
api.add_router("admin/add/", admin_add_router)

from .views.transactions import router as transactions_router

api.add_router("transactions/", transactions_router)

urlpatterns = [
    path("", api.urls),
]
