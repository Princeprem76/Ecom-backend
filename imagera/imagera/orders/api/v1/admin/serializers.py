from imagera.orders.api.v1.serializers import (
    CartItemsSerializer,
    DropLocationSerializer,
    OrderPaymentViewSerializer,
)
from imagera.orders.models import (
    ExpressShippingCharge,
    # ExpressShippingPlace,
    Orders,
    ReturnProductRequest,
    ShippingType,
    # StandardFreeDeliveryCities,
    # StandardFreeDeliveryPlace,
    StandardShippingCharge,
)
from rest_framework import serializers
# from imagera.payments.signals import delivery_completed, out_for_delivery
from imagera.payments.models import OrderPayment
from imagera.users.models import User


class OrderUser(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email"]


class AdminShippingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingType
        fields = ["shipping_type"]


class AdminConfirmedOrderSerializer(serializers.ModelSerializer):
    item = CartItemsSerializer(read_only=True, many=True)
    payment = OrderPaymentViewSerializer(
        source="order_payment", read_only=True, many=True
    )
    drop_location = DropLocationSerializer(read_only=True)
    shipping = AdminShippingSerializer()
    order_by = OrderUser()

    class Meta:
        model = Orders
        fields = [
            "id",
            "item",
            "order_date",
            "order_price",
            "order_status",
            "order_by",
            "payment",
            "drop_location",
            "shipping",
            "delivered_by",
        ]
        read_only_fields = ["delivered_by"]


class UpdateOrderStatusSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    order_status = serializers.CharField(max_length=255)

    def provide_purchase_reward(self, order):
        final_price = order.order_price - order.shipping.price
        purchase_amount = final_price  # Assuming this field holds the total order price
        user = order.order_by

        user_profile = user.users_rewards

        if 1000 <= purchase_amount < 5000:
            user_profile.silver_coins += 1
        elif 5000 <= purchase_amount < 15000:
            user_profile.gold_coins += 1
        elif purchase_amount >= 50000:
            user_profile.diamond_coins += 1
        user_profile.save()
        return order

    def create(self, validated_data):
        order = Orders.objects.get(id=validated_data["order_id"])
        order.order_status = validated_data["order_status"]
        payment = OrderPayment.objects.get(order_code=order)
        if validated_data["order_status"] == "Delivered":
            if payment.payment_method == "cod":
                payment.is_paid = True
                payment.save()
            self.provide_purchase_reward(order)
        order.save()
        return validated_data


class AdminReturnProductSerializer(serializers.ModelSerializer):
    request_id = serializers.CharField(max_length=10, write_only=True)
    status = serializers.CharField(max_length=100)
    product = CartItemsSerializer(read_only=True)
    order_code = AdminConfirmedOrderSerializer(read_only=True)

    class Meta:
        model = ReturnProductRequest
        fields = "__all__"
        read_only_fields = [
            "product",
            "order_code",
            "pickup_location",
            "district",
            "city",
            "contact",
            "created_at",
            "reason",
            "images",
            "user",
        ]

    def create(self, validated_data):
        return_product_request = ReturnProductRequest.objects.get(
            id=validated_data["request_id"]
        )
        return_product_request.status = validated_data["status"]
        return_product_request.save()
        return validated_data


# class AdminStandardFreeDeliverySerializer(serializers.ModelSerializer):
#     city_list = serializers.ListField(
#         child=serializers.CharField(max_length=100), write_only=True
#     )
#     cities = serializers.CharField(
#         source="standard_free_delivery_cities.city", read_only=True
#     )

#     class Meta:
#         model = StandardFreeDeliveryPlace
#         fields = "__all__"
#         read_only_fields = ["cities"]

#     def create(self, validated_data):
#         city_list = validated_data.pop("city_list")
#         district_data = StandardFreeDeliveryPlace.objects.create(
#             district=validated_data["district"]
#         )
#         for place in city_list:
#             city, _ = StandardFreeDeliveryCities.objects.get_or_create(city=place)
#             district_data.cities.add(city)
#         return validated_data


class AdminStandardShippingChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardShippingCharge
        fields = "__all__"

    def create(self, validated_data):
        shipping_charge = StandardShippingCharge.objects.create(
            shipping_type="Normal", **validated_data
        )
        return validated_data


# class AdminExpressShippingPlaceSerializer(serializers.ModelSerializer):
#     city_list = serializers.ListField(
#         child=serializers.CharField(max_length=100), write_only=True
#     )
#     cities = serializers.CharField(
#         source="express_shipping_place_cities.city", read_only=True
#     )

#     class Meta:
#         model = ExpressShippingPlace
#         fields = "__all__"
#         read_only_fields = ["cities"]

#     def create(self, validated_data):
#         city_list = validated_data.pop("city_list")
#         district_data = ExpressShippingPlace.objects.create(
#             district=validated_data["district"]
#         )
#         for place in city_list:
#             city, _ = StandardFreeDeliveryCities.objects.get_or_create(city=place)
#             district_data.cities.add(city)
#         return validated_data

class AdminExpressShippingChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpressShippingCharge
        fields = "__all__"