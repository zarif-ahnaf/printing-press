from django.urls import path

from ninja import NinjaAPI


api = NinjaAPI(
    title="PrintingPress",
)

from .views.balance import router as balance_router

api.add_router("balance/", balance_router)


from .views.count import router as count_router

api.add_router("count/", count_router)

from .views.charge import router as charge_router

api.add_router("charge/", charge_router)

from .views.user.login import router as login_router
from .views.user.logout import router as logout_router

api.add_router("user/", login_router)
api.add_router("user/", logout_router)

from .views.admin.charge import router as admin_charge_router
from .views.admin.deposit import router as admin_deposit_router

api.add_router("admin/deposit/", admin_deposit_router)
api.add_router("admin/charge/", admin_charge_router)

from .views.transactions import router as transactions_router

api.add_router("transactions/", transactions_router)

urlpatterns = [
    path("", api.urls),
]
