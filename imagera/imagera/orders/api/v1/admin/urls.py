from django.urls import path
from rest_framework.routers import DefaultRouter

from imagera.orders.api.v1.admin.views import (
    AdminCurrentOrderView,
    AdminRetrieveOrderHistory,
    AdminReturnProdutsView,
    # CreateExpressShippingPlace,
    CreateExpresshippingCharge,
    CreateStandardShippingCharge,
    # CreateStandardShippingPlace,
    # UpdateDeleteExpressShippingPlace,
    UpdateDeleteStandardShippingCharge,
    UpdateExpressShippingCharge,
    UpdateOrderStatus,
    CreateShippingType,
    ViewTopBuyer,
)


app_name = "admin-orders"

router = DefaultRouter()

urlpatterns = [
    path(
        "order-history/",
        AdminRetrieveOrderHistory.as_view(),
        name="admin_order_history",
    ),
    path(
        "current-order/",
        AdminCurrentOrderView.as_view(),
        name="admin_current_order",
    ),
    path(
        "update-status/",
        UpdateOrderStatus.as_view(),
        name="update_status",
    ),
    path(
        "return-product-update/",
        AdminReturnProdutsView.as_view(),
        name="admin_return_product_update",
    ),
    path(
        "create-shippingtype/",
        CreateShippingType.as_view(),
        name="create_shipping_type",
    ),
    path(
        "create-standard-shippng-charge/",
        CreateStandardShippingCharge.as_view(),
        name="create_standard_shipping_charge",
    ),
    path(
        "update-standard-shippng-charge/<int:pk>/",
        UpdateDeleteStandardShippingCharge.as_view(),
        name="update_delete_standard_shipping_charge",
    ),
    # path(
    #     "create-express-shipping-place/",
    #     CreateExpressShippingPlace.as_view(),
    #     name="create_express_shipping_place",
    # ),
    # path(
    #     "update-express-shipping-place/<int:pk>/",
    #     UpdateDeleteExpressShippingPlace.as_view(),
    #     name="update_delete_express_shipping_place",
    # ),
    # path(
    #     "create-standard-shipping-place/",
    #     CreateStandardShippingPlace.as_view(),
    #     name="create_standard_shipping_place",
    # ),
    # path(
    #     "update-standard-shipping-place/<int:pk>/",
    #     UpdateDeleteExpressShippingPlace.as_view(),
    #     name="update_delete_standard_shipping_place",
    # ),
    path(
        "create-express-charge/",
        CreateExpresshippingCharge.as_view(),
        name="create_express_shipping_charge",
    ),
    path(
        "update-express-shipping-charge/<int:pk>/",
        UpdateExpressShippingCharge.as_view(),
        name="update_express_shipping_charge",
    ),
    path(
        "top-buyers/",
        ViewTopBuyer.as_view(),
        name="top_buyer",
    ),
]

urlpatterns += router.urls
