from django.contrib import admin

from imagera.orders.models import (
    ShippingType,
    Orders,
    DropLocation,
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
       
        StandardShippingCharge,
        ExpressShippingCharge,
      
        Coupon,
        ReturnProductRequest,
    ]
)
