from rest_framework import serializers
# from imagera.payments.signals import payment_completed
from imagera.core.payment_gateway import EsewaTransaction, KhaltiTransaction
from imagera.core.utils import Util
from imagera.orders.models import CustomerCouponUsed, Orders
from imagera.payments.models import OrderPayment
from rest_framework.exceptions import ValidationError
import datetime


class OrderPaymentSerializer(serializers.Serializer):
    payment_method = serializers.CharField(max_length=120)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_code = serializers.CharField(max_length=255)
    ref_code = serializers.CharField(max_length=255, required=False)
    pidx = serializers.CharField(
        max_length=255, required=False, help_text="For only khalti"
    )

    def validate(self, data):
        if self.context["price"] != data.get("amount"):
            raise ValidationError("Paid price is less than Actual Price!")
        return data

    def create(self, validated_data):
        ordercode = Orders.objects.get(order_code=validated_data["order_code"])
        total_original_price = 0
        if validated_data["payment_method"] == "esewa":
            check = EsewaTransaction.validate(
                order_id=validated_data["order_code"],
                total_amount=validated_data["amount"],
                transaction_uuid=validated_data["ref_code"],
            )
            if check == "Complete":
                OrderPayment.objects.create(
                    user=self.context["request"].user,
                    payment_method="esewa",
                    order_code=ordercode,
                    payment_token=validated_data["ref_code"],
                    is_paid=True,
                    amount=validated_data["amount"],
                )
            else:
                raise ValidationError("Invalid Esewa Transaction")
        elif validated_data["payment_method"] == "cod":
            OrderPayment.objects.create(
                user=self.context["request"].user,
                payment_method="cod",
                order_code=ordercode,
                is_paid=False,
                amount=int(validated_data["amount"]) + 10,
            )
            ordercode.order_price += 10
        elif validated_data["payment_method"] == "khalti":
            check = KhaltiTransaction.validate(
                pidx=validated_data["pidx"],
            )
            if check == "Complete":
                OrderPayment.objects.create(
                    user=self.context["request"].user,
                    payment_method="khalti",
                    order_code=ordercode,
                    is_paid=True,
                    payment_token=validated_data["pidx"],
                    amount=validated_data["amount"],
                )
            else:
                raise ValidationError("Invalid Khalti Transaction")
        else:
            raise ValidationError("Invalid Payment Method")

        ordercode.order_confirmed = True
        ordercode.order_status = "Processing"
        if ordercode.coupon:
            CustomerCouponUsed.objects.create(
                user=self.context["request"].user, coupon_code=ordercode.coupon
            )
        if ordercode.coins_used:
            user_profile = self.context["request"].user.users_rewards
            user_profile.diamond_coins -= ordercode.coins_used
            user_profile.save()
        
        for it in ordercode.item.all():
            it.current_order = True
            it.item.product_quantity -= it.quantity
            it.save()
            it.item.save()
            total_original_price += it.quantity * it.item.product_price
        discount_price = (
            ordercode.order_price - ordercode.delivery_charge - total_original_price
        )
        ordercode.save()
        try:
            # payment_completed.send(
            #     sender=None,
            #     user=self.context["request"].user,
            #     order_info=ordercode.order_code,
            # )
            Util.send_purchase_invoice(
                order=ordercode,
                discount=discount_price,
                payment_method=validated_data["payment_method"],
            )
        except:
            pass
        return validated_data


def check_expiry_month(value):
    if not 1 <= int(value) <= 12:
        raise serializers.ValidationError("Invalid expiry month.")


def check_expiry_year(value):
    today = datetime.datetime.now()
    if not int(value) >= today.year:
        raise serializers.ValidationError("Invalid expiry year.")


def check_cvc(value):
    if not 3 <= len(value) <= 4:
        raise serializers.ValidationError("Invalid cvc number.")


def check_payment_method(value):
    payment_method = value.lower()
    if payment_method not in ["card"]:
        raise serializers.ValidationError("Invalid payment_method.")


class CardInformationSerializer(serializers.Serializer):
    card_number = serializers.CharField(max_length=150, required=True)
    expiry_month = serializers.CharField(
        max_length=150,
        required=True,
        validators=[check_expiry_month],
    )
    expiry_year = serializers.CharField(
        max_length=150,
        required=True,
        validators=[check_expiry_year],
    )
    cvc = serializers.CharField(
        max_length=150,
        required=True,
        validators=[check_cvc],
    )

    def create_checkout(self, order, price):
        OrderPayment.objects.create(
            user=self.context["request"].user,
            payment_method="stripe",
            order_code=order.order_code,
            is_paid=True,
            amount=price,
        )
        ordercode = order
        ordercode.order_confirmed = True
        ordercode.order_status = "Processing"
        if ordercode.coupon:
            CustomerCouponUsed.objects.create(
                user=self.context["request"].user, coupon_code=ordercode.coupon
            )
        if ordercode.coins_used:
            try:
                user_profile = self.context["request"].user.userrewards
                user_profile.diamond_coins -= ordercode.coins_used
                user_profile.save()
            except:
                raise ValidationError("Invalid Diamond Coins")
        
        for it in ordercode.item.all():
            it.current_order = True
            it.item.product_quantity -= it.quantity
            it.save()
            it.item.save()
            total_original_price += it.quantity * it.item.product_price
        discount_price = (
            ordercode.order_price - ordercode.delivery_charge - total_original_price
        )
        ordercode.save()
        try:
            # payment_completed.send(
            #     sender=None,
            #     user=self.context["request"].user,
            #     order_info=ordercode.order_code,
            # )
            Util.send_purchase_invoice(
                order=ordercode,
                discount=discount_price,
                payment_method="stripe",
            )
        except:
            pass
        return order
