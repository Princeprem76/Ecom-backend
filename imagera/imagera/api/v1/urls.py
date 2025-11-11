from django.urls import path, include


app_name = "api_v1"

urlpatterns = [
    path("user/", include("imagera.users.api.v1.urls", namespace="user")),
    path("products/", include("imagera.product.api.v1.urls", namespace="products")),
    path(
        "admin-products/",
        include("imagera.product.api.v1.admin.urls", namespace="admin_products"),
    ),
    # path("blogs/", include("imagera.blog.api.v1.urls", namespace="blog")),
    path("orders/", include("imagera.orders.api.v1.urls", namespace="orders")),
    path(
        "admin-orders/",
        include("imagera.orders.api.v1.admin.urls", namespace="admin_orders"),
    ),
    path("payments/", include("imagera.payments.api.v1.urls", namespace="payments")),
   
]
