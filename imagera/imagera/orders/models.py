from django.db import models

# Create your models here.
from imagera.core.models import TimeStampAbstractModel
from imagera.product.models import Products, ProductVariations
from imagera.users.models import User
from nepali_municipalities import NepalMunicipality
from django.utils import timezone
from datetime import timedelta, time

from dateutil.relativedelta import relativedelta

# Fetch all districts from the library
all_districts = NepalMunicipality().all_districts()
all_data = []
for district in all_districts:
    all_municipalities = NepalMunicipality(district).all_municipalities()
    for municipality in all_municipalities:
        all_data.append(municipality)



# Create choices tuple
DISTRICT_CHOICES = [(district, district) for district in all_districts]
MUNICIPALITY_CHOICES = [
    (municipality, municipality) for municipality in all_data
]

SHIPPING_TYPE_CHOICES = [
    ("Normal", "Normal"),
    ("Express", "Express"),
]


class DropLocation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
    )
    email = models.EmailField(null=True)
    name = models.CharField(max_length=255)
    phone = models.PositiveBigIntegerField()
    full_address = models.CharField(max_length=250)
    district = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100)
    label = models.CharField(max_length=255, null=True)

    # def __str__(self):
    #     return str(self.drop_location)


# class StandardFreeDeliveryCities(models.Model):
#     city = models.CharField(max_length=100)


# class StandardFreeDeliveryPlace(models.Model):
#     district = models.CharField(max_length=255)
#     cities = models.ManyToManyField(StandardFreeDeliveryCities)

#     def __str__(self):
#         return str(self.district)


class ShippingType(models.Model):
    shipping_type = models.CharField(max_length=255, choices=SHIPPING_TYPE_CHOICES)

    def __str__(self):
        return str(self.shipping_type)


class StandardShippingCharge(models.Model):
    base_charge = models.PositiveIntegerField(default=0)
    # per_kg_charge = models.PositiveIntegerField(default=0)


# class ExpressShippingPlace(models.Model):
#     district = models.CharField(max_length=255)
#     cities = models.ManyToManyField(StandardFreeDeliveryCities)


class ExpressShippingCharge(models.Model):
    charge = models.PositiveIntegerField()


class Items(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    item = models.ForeignKey(
        ProductVariations,
        on_delete=models.SET_NULL,
        null=True,
    )
    quantity = models.PositiveIntegerField(default=0)
    current_order = models.BooleanField(default=False)

    def __str__(self):
        return self.item.product.product_name

    def get_discounted_price(self):
        base_price = self.item.product_price
        discounted_price = base_price

        product_discount = self.item.product.product_discount
        product_discount_amount = (
            product_discount * 0.01 * base_price if product_discount else 0
        )

        sub_category = self.item.product.sub_category
        sub_category_discount_amount = 0
        if (
            sub_category
            and sub_category.is_discount_active()
            and product_discount_amount != 0
        ):
            sub_category_discount = self._get_total_subcategory_discount(sub_category)
            sub_category_discount_amount = (
                sub_category_discount * 0.01 * (product_discount_amount)
            )
            product_discount_amount += sub_category_discount_amount
        elif (
            sub_category
            and sub_category.is_discount_active()
            and product_discount_amount == 0
        ):
            sub_category_discount = self._get_total_subcategory_discount(sub_category)
            sub_category_discount_amount = sub_category_discount * 0.01 * (base_price)
            product_discount_amount += sub_category_discount_amount

        category = self.item.product.product_category
        category_discount_amount = 0
        if category and category.is_discount_active() and product_discount_amount != 0:
            category_discount = category.category_discount
            category_discount_amount = (
                category_discount * 0.01 * (product_discount_amount)
            )
            product_discount_amount += category_discount_amount
        elif (
            category and category.is_discount_active() and product_discount_amount == 0
        ):
            category_discount = category.category_discount
            category_discount_amount = (
                category_discount * 0.01 * (product_discount_amount)
            )
            product_discount_amount += category_discount_amount

        discounted_price -= product_discount_amount
        discounted_price = max(0, discounted_price)

        return discounted_price

    def get_total(self):
        return self.quantity * self.item.product_price
    
    def _get_total_subcategory_discount(self, sub_category):
        total_discount_percent = 0
        while sub_category:
            if sub_category.is_discount_active():
                subcategory_discount = sub_category.sub_category_discount
                if total_discount_percent !=0:
                    parent_discount_percent = subcategory_discount * (total_discount_percent / 100)
                else:
                    parent_discount_percent = subcategory_discount
                total_discount_percent += parent_discount_percent
            sub_category = sub_category.parent_sub_category
        return total_discount_percent

    def get_total_discount(self):
        return self.quantity * self.item.get_discounted_price()["discount_amount"]


class Coupon(models.Model):
    coupon_number = models.CharField(max_length=8)
    discount = models.PositiveSmallIntegerField()
    generated_date = models.DateTimeField(auto_now=True)
    expiry_date = models.DateTimeField()

    def __str__(self):
        return str(self.coupon_number)


class CustomerCouponUsed(TimeStampAbstractModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon_code = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True)
    used_date = models.DateField(auto_now=True)


class Orders(models.Model):
    ORDER_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SHIPPED", "Shipped"),
        ("OUTFORDELIVERY", "OutForDelivery"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]
    order_status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending"
    )
    order_code = models.CharField(max_length=10, null=True)
    order_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    item = models.ManyToManyField(Items)
    order_date = models.DateTimeField(null=True, auto_now=True)
    order_confirmed = models.BooleanField(default=False)
    drop_location = models.ForeignKey(
        DropLocation, on_delete=models.SET_NULL, null=True
    )
    order_price = models.PositiveBigIntegerField(default=0)
    shipping = models.ForeignKey(ShippingType, on_delete=models.SET_NULL, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    delivery_charge = models.PositiveBigIntegerField(default=0)
    cashback_applied = models.BooleanField(default=False)
    coins_used = models.IntegerField(null=True, blank=True)
    # def __str__(self):
    #     return self.order_by.email

    def delivered_by(self):
        order_datetime = self.order_date
        delivery_start = None
        delivery_end = None
        start_time = time(10, 0)  # 10 AM
        end_time = time(18, 0)  # 6 PM

        order_time = order_datetime.time()
        if start_time <= order_time <= end_time:
            additional_hours = 12
        else:
            additional_hours = 18
        if order_datetime.weekday() == 5:
            additional_hours += 24
        if self.shipping.shipping_type == "Normal":
            delivery_start = self.order_date + relativedelta(days=1)
            delivery_end = self.order_date + relativedelta(days=4)
        else:
            delivery_start = self.order_date + timedelta(hours=additional_hours)
            delivery_end = self.order_date + timedelta(hours=(additional_hours + 2))
        response = {"delivery_start": delivery_start, "delivery_end": delivery_end}
        return response


class ForbiddenDelivery(models.Model):
    product = models.ForeignKey(
        Products, on_delete=models.CASCADE, related_name="forbidden_product_delivery"
    )
    district = models.CharField(max_length=255, choices=DISTRICT_CHOICES)



# return
class ReturnProductRequest(models.Model):
    RETURN_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("PICKUP", "Pickup"),
        ("RESOLVED", "Resolved"),
        ("CANCELLED", "Cancelled"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_returned_product"
    )
    product = models.ForeignKey(
        ProductVariations, on_delete=models.CASCADE, related_name="returned_product"
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    order_code = models.ForeignKey(
        Orders, on_delete=models.CASCADE, related_name="returned_order"
    )
    pickup_location = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    contact = models.CharField(max_length=20)
    status = models.CharField(
        max_length=255, choices=RETURN_STATUS_CHOICES, default="Pending"
    )


class ReturnProductImage(models.Model):
    return_product = models.ForeignKey(
        ReturnProductRequest,
        on_delete=models.CASCADE,
        related_name="returned_product_image",
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="return_product/", null=True, blank=True)
