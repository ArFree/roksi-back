from django.urls import path, include
from rest_framework import routers

from order.views import OrderCreateView, PaymentViewSet, OrderListView

router = routers.DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")


urlpatterns = [
    path("create/", OrderCreateView.as_view(), name="create-order"),
    path("orders/", OrderListView.as_view(), name="orders"),
    path("", include(router.urls))
]

app_name = "order"
