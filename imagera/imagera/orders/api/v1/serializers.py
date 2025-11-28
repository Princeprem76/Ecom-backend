from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
from imagera.orders.models import (
    Coupon,
    CustomerCouponUsed,
    DropLocation,
    ExpressShippingCharge,
    ForbiddenDelivery,
    Items,
    Orders,
    ReturnProductImage,
    ReturnProductRequest,
    ShippingType,
    StandardShippingCharge,
)
from imagera.payments.models import OrderPayment
from imagera.product.api.v1.serializers import (
    LaptopProductsSerializer,
    ProductImagesSerializer,
)
from imagera.product.models import (
    ComboDiscount,
    ProductVariations,
    Products,
    # UserSubscription,
)
from rest_framework.exceptions import ValidationError
from decimal import Decimal
import string
import random


def generate_alphanumeric_code(length=7):
    characters = string.ascii_uppercase + string.digits  # Uppercase letters and digits
    return "".join(random.choices(characters, k=length))


class DropLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DropLocation
        fields = [
            "id",
            "email",
            "name",
            "phone",
            "full_address",
            "district",
            "city",
            "label",
        ]

    def create(self, validated_data):
        drop_location = DropLocation.objects.create(
            user=self.context["request"].user, **validated_data
        )
        return validated_data


class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = ["id", "product_name", "product_description", "brand"]


class ProductVariationSerializer(serializers.ModelSerializer):
    product = OrderProductSerializer(read_only=True)
    laptop_product = LaptopProductsSerializer(read_only=True)
    product_images = ProductImagesSerializer(many=True, read_only=True)
    stock = serializers.SerializerMethodField("get_product_quantity")

    class Meta:
        model = ProductVariations
        fields = [
            "id",
            "product",
            "product_color",
            "product_size",
            "product_price",
            "laptop_product",
            "product_images",
            "get_image_count",
            "get_discounted_price",
            "stock",
        ]

    def get_product_quantity(self, obj):
        quantity = obj.product_quantity
        if quantity == 0:
            response_data = {"quantity": quantity, "text": "Out of Stock"}
        elif quantity <= 5:
            response_data = {"quantity": quantity, "text": "Low on stock"}
        else:
            response_data = {"quantity": quantity, "text": "In stock"}

        return response_data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # request = self.context.get("request", None)

        # if request and hasattr(request, "user") and request.user.is_authenticated:
        #     user = request.user
        #     if user.user_type != 4:
        #         representation.pop("business_product", None)
        # else:
        #     representation.pop("business_product", None)
        return representation


class CartItemsSerializer(serializers.ModelSerializer):
    item = ProductVariationSerializer(read_only=True)

    class Meta:
        model = Items
        fields = ["id", "item", "quantity"]


class AddCartItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(write_only=True)
    quantity = serializers.IntegerField(default=1, write_only=True)


class AddCartItemsSerializer(serializers.Serializer):
    items = AddCartItemSerializer(many=True, write_only=True)


class ReduceItemQuantitySerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)


class CreateOrderSerializer(serializers.Serializer):
    coupon = serializers.CharField(max_length=255, required=False)
    rewards = serializers.IntegerField(required=False)

    def validate(self, data):
        coupon_code = data.get("coupon", None)
        if coupon_code:
            try:
                coupon = Coupon.objects.get(coupon_number=coupon_code)
                if coupon.expiry_date < timezone.now():
                    raise ValidationError("Coupon has expired.")
                if CustomerCouponUsed.objects.filter(
                    user=self.context["request"].user, coupon_code=coupon
                ).exists():
                    raise ValidationError("Coupon has already been used.")
            except Coupon.DoesNotExist:
                raise ValidationError("Invalid coupon.")
        order_exists = Orders.objects.filter(
            order_by=self.context["request"].user, order_status="Pending"
        )
        if order_exists:
            order_exists.first().delete()
        items = Items.objects.filter(
            user=self.context["request"].user, current_order=False
        )
        for item in items:
            item_quantity = item.quantity
            product_variation_quantity = item.item.product_quantity
            if item_quantity > product_variation_quantity:
                raise ValidationError(
                    f"Quantity of {item.item.product_name} exceeds available quantity."
                )
        return data

    def get_combo_discounts(self, queryset):
        combo_discounts_applied = []
        combo_discount_amount = 0

        combo_discounts = ComboDiscount.objects.filter(
            products__product_variations__in=[item.item for item in queryset]
        ).distinct()

        for combo_discount in combo_discounts:
            combo_product_ids = set(
                combo_discount.products.values_list("id", flat=True)
            )
            cart_product_ids = set(queryset.values_list("item__product__id", flat=True))

            if combo_product_ids.issubset(cart_product_ids):
                discount_percentage = combo_discount.discount_percentage
                for item in queryset:
                    if item.item.product.id in combo_product_ids:
                        discounted_price = (
                            1 - discount_percentage * 0.01
                        ) * item.get_discounted_price()
                        combo_discount_amount += (
                            item.get_discounted_price() - discounted_price
                        ) * item.quantity
                        combo_discounts_applied.append(
                            {
                                "combo": combo_discount,
                                "product": item.item.product,
                                "discounted_price": discounted_price,
                                "quantity": item.quantity,
                            }
                        )

        return combo_discount_amount, combo_discounts_applied

    def get_total_price(self, queryset):
        total_price = 0
        total_discount = 0
        total_amount = 0
        combo_discount_amount, combo_discounts_applied = self.get_combo_discounts(
            queryset
        )

        combo_product_ids = set(item["product"].id for item in combo_discounts_applied)

        for item in queryset:
            if item.item.product.id not in combo_product_ids:
                product_discounted_price = item.item.get_discounted_price()[
                    "discount_amount"
                ]
                item_total = item.quantity * product_discounted_price

                total_price += (
                    item.quantity * item.item.get_discounted_price()["final_price"]
                )
                total_amount += item_total
            else:
                total_price += (
                    item.quantity * item.item.get_discounted_price()["final_price"]
                )

        total_amount += combo_discount_amount
        total_discount = total_amount
        final_price = total_price - combo_discount_amount

        serializer = CartItemsSerializer(queryset, many=True)
        response = {
            "data": serializer.data,
            "summary": {
                "total_price": total_price,
                "total_discount_amount": total_discount,
                "total_combo_discount_amount": combo_discount_amount,
                "final_total_price": final_price,
            },
        }

        # subscription = UserSubscription.objects.filter(
        #     user=self.context["request"].user
        # ).first()
        # if subscription and subscription.is_active():
        #     sub_discount = (
        #         subscription.subscription.subscription_discount * 0.01 * final_price
        #     )
        #     final_price -= sub_discount
        if "coupon" in self.validated_data:
            coupon = Coupon.objects.get(coupon_number=self.validated_data["coupon"])
            final_price -= coupon.discount

        return final_price

    def create(self, validated_data):
        shiping_type = ShippingType.objects.get(shipping_type="Normal")
        order_code = generate_alphanumeric_code()
        if "coupon" in validated_data:
            coupon = Coupon.objects.get(coupon_number=validated_data["coupon"])
        order = Orders.objects.create(
            order_by=self.context["request"].user,
            order_status="Pending",
            coupon=coupon if "coupon" in validated_data else None,
            shipping=shiping_type,
            order_code=order_code,
            coins_used=(
                validated_data["rewards"] if "rewards" in validated_data else None
            ),
        )
        queryset = Items.objects.filter(
            user=self.context["request"].user, current_order=False
        )
        for item_data in queryset:
            item = Items.objects.get(id=item_data.id)
            order.item.add(item)

        order.order_price = Decimal(self.get_total_price(queryset=queryset))
        order.save()
        return order


class UpdateOrderSerializer(serializers.Serializer):
    drop_location_id = serializers.CharField(max_length=255, write_only=True)
    shipping = serializers.CharField(max_length=255, write_only=True, required=False)

    def create(self, validated_data):
        order = Orders.objects.filter(
            order_by=self.context["request"].user,
            order_status="Pending",
        ).first()
        drop_location = DropLocation.objects.get(id=validated_data["drop_location_id"])
        order.order_price += StandardShippingCharge.base_charge
        order.delivery_charge = StandardShippingCharge.base_charge
        
        order.drop_location = drop_location
        if "shipping" in validated_data and validated_data["shipping"]:
            shipping_type = ShippingType.objects.get(
                shipping_type=validated_data["shipping"]
            )
            order.shipping = shipping_type
            if shipping_type.shipping_type == "Express":
                express_price = ExpressShippingCharge.objects.all().first()
                order.order_price += express_price.charge
                order.delivery_charge += express_price.charge
        order.save()
        return validated_data


class OrderSerializer(serializers.ModelSerializer):
    item = CartItemsSerializer(read_only=True, many=True)

    class Meta:
        model = Orders
        fields = [
            "item",
            "order_date",
            "order_price",
            "order_code",
            "delivered_by",
            "delivery_charge",
        ]
        read_only_fields = ["delivered_by", "delivery_charge"]


class OrderPaymentViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderPayment
        fields = [
            "payment_method",
            "payment_date",
            "payment_token",
            "is_paid",
        ]


class ConfirmedOrderSerializer(serializers.ModelSerializer):
    item = CartItemsSerializer(read_only=True, many=True)
    payment = OrderPaymentViewSerializer(
        source="order_payment", read_only=True, many=True
    )
    drop_location = DropLocationSerializer(read_only=True)

    class Meta:
        model = Orders
        fields = [
            "item",
            "order_date",
            "order_price",
            "order_code",
            "order_status",
            "payment",
            "drop_location",
            "delivered_by",
        ]
        read_only_fields = ["delivered_by"]


class DistrictSerializer(serializers.Serializer):
    district_choices = serializers.ListField(child=serializers.CharField())


class DistrictSerializer(serializers.Serializer):
    municipality_choices = serializers.ListField(child=serializers.CharField())


class ReturnProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnProductImage
        fields = [
            "image",
        ]


class ReturnProductSerializer(serializers.ModelSerializer):
    ordercode = serializers.CharField(max_length=10, write_only=True)
    productvariation_id = serializers.CharField(max_length=100, write_only=True)
    product = CartItemsSerializer(read_only=True)
    order_code = ConfirmedOrderSerializer(read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(write_only=True, required=False),
        write_only=True,
        required=False,
    )

    class Meta:
        model = ReturnProductRequest
        fields = [
            "id",
            "product",
            "reason",
            "uploaded_images",
            "created_at",
            "order_code",
            "pickup_location",
            "district",
            "city",
            "contact",
            "status",
            "ordercode",
            "productvariation_id",
        ]
        read_only_fields = ["product", "order_code", "status"]

    def validate(self, data):
        order_code = data.get("ordercode")
        productvariation_id = data.get("productvariation_id")
        product_variation = ProductVariations.objects.filter(id=productvariation_id)
        order = Orders.objects.filter(
            order_code=order_code, order_by=self.context["request"].user
        )
        if not order:
            raise ValidationError("Order does not exists!")
        if not productvariation_id:
            raise ValidationError("Product does not exists!")
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        ordercode = validated_data.pop("ordercode")
        variation_id = validated_data.pop("productvariation_id")
        images = validated_data.pop("uploaded_images", None)
        order = Orders.objects.filter(
            order_code=ordercode, order_by=self.context["request"].user
        )
        return_product_request = ReturnProductRequest.objects.create(
            user=user,
            product_id=variation_id,
            order_code=order.first(),
            **validated_data,
        )
        for img in images:
            ReturnProductImage.objects.create(
                return_product=return_product_request, image=img
            )
        return validated_data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["images"] = ReturnProductImageSerializer(
            instance.returned_product_image.all(), many=True, context=self.context
        ).data
        return representation
