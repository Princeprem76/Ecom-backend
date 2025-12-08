from django.contrib import admin

from imagera.orders.models import (
    ShippingType,
    Orders,
    DropLocation,
    Items,
    # StandardFreeDeliveryCities,
    # StandardFreeDeliveryPlace,
    StandardShippingCharge,
    ExpressShippingCharge,
    # ExpressShippingPlace,
    Coupon,
    ReturnProductRequest,
)

# Register your models here.
admin.site.register(
    [
        ShippingType,
        Orders,
        DropLocation,
        Items,
       
        StandardShippingCharge,
        ExpressShippingCharge,
      
        Coupon,
        ReturnProductRequest,
    ]
)
