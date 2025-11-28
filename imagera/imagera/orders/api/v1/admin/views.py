from imagera.orders.api.v1.admin.serializers import (
    AdminConfirmedOrderSerializer,
    AdminExpressShippingChargeSerializer,
    # AdminExpressShippingPlaceSerializer,
    AdminReturnProductSerializer,
    AdminShippingSerializer,
    # AdminStandardFreeDeliverySerializer,
    AdminStandardShippingChargeSerializer,
    UpdateOrderStatusSerializer,
)
from imagera.orders.models import (
    ExpressShippingCharge,
  
    Items,
    Orders,
    ReturnProductRequest,
    ShippingType,
   
    StandardShippingCharge,
)
from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    UpdateAPIView,
    RetrieveUpdateDestroyAPIView,
    ListCreateAPIView,
)
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from django.db.models import Q, Sum, Count
from datetime import timedelta

from imagera.users.forms import User


class AdminCurrentOrderView(ListAPIView):
    serializer_class = AdminConfirmedOrderSerializer
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        searched_order = self.request.query_params.get("order_code", None)
        queryset = (
            Orders.objects.filter(
                order_confirmed=True,
            )
            .filter(
                Q(order_status__iexact="Processing") | Q(order_status__iexact="Shipped")
            )
            .order_by("-order_date")
        )
        if searched_order:
            queryset = queryset.filter(order_code__iexact=searched_order)
        return queryset

    @extend_schema(
        operation_id="Current Order",
        description="""
            Allows to search and get all current running order
        """,
        parameters=[
            OpenApiParameter(
                name="order_code",
                required=False,
                type=str,
                description="Order Code",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class AdminRetrieveOrderHistory(ListAPIView):
    serializer_class = AdminConfirmedOrderSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        searched_order = self.request.query_params.get("order_code", None)
        queryset = Orders.objects.filter(
            order_status__iexact="Delivered", order_confirmed=True
        ).order_by("-order_date")
        if searched_order:
            queryset = queryset.filter(order_code__iexact=searched_order)
        return queryset

    @extend_schema(
        operation_id="Order History",
        description="""
            Allows to search and get all completed order
        """,
        parameters=[
            OpenApiParameter(
                name="order_code",
                required=False,
                type=str,
                description="Order Code",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class UpdateOrderStatus(CreateAPIView):
    serializer_class = UpdateOrderStatusSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Order status updated successfully"}, status=status.HTTP_200_OK
        )


class AdminReturnProdutsView(ListCreateAPIView):
    serializer_class = AdminReturnProductSerializer
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Product return request updated"},
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, *args, **kwargs):
        queryset = ReturnProductRequest.objects.all()
        serializer = AdminReturnProductSerializer(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class CreateShippingType(ListCreateAPIView):
    serializer_class = AdminShippingSerializer
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Shipping type created"}, status=status.HTTP_201_CREATED
        )

    def get(self, request, *args, **kwargs):
        queryset = ShippingType.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class CreateStandardShippingCharge(ListCreateAPIView):
    serializer_class = AdminStandardShippingChargeSerializer
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Standard shipping charge created"},
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, *args, **kwargs):
        queryset = StandardShippingCharge.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class UpdateDeleteStandardShippingCharge(RetrieveUpdateDestroyAPIView):
    serializer_class = AdminStandardShippingChargeSerializer
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]
    queryset = StandardShippingCharge.objects.all()
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"detail": "Updated!"}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Delivery Charge has been deleted!"}, status=status.HTTP_200_OK
        )


# class CreateExpressShippingPlace(ListCreateAPIView):
#     serializer_class = AdminExpressShippingPlaceSerializer
#     permission_classes = [
#         IsAuthenticated,
#         IsAdminUser,
#     ]

#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(
#             {"message": "Express Shipping Place created"},
#             status=status.HTTP_201_CREATED,
#         )

#     def get(self, request, *args, **kwargs):
#         queryset = ExpressShippingPlace.objects.all()
#         serializer = self.serializer_class(queryset, many=True)
#         return Response({"data": serializer.data}, status=status.HTTP_200_OK)


# class UpdateDeleteExpressShippingPlace(RetrieveUpdateDestroyAPIView):
#     serializer_class = AdminExpressShippingPlaceSerializer
#     permission_classes = [
#         IsAuthenticated,
#         IsAdminUser,
#     ]
#     queryset = ExpressShippingPlace.objects.all()
#     lookup_field = "pk"

#     def update(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance, data=request.data, partial=True)
#         serializer.is_valid(raise_exception=True)
#         self.perform_update(serializer)
#         return Response({"detail": "Updated!"}, status=status.HTTP_200_OK)

#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         self.perform_destroy(instance)
#         return Response(
#             {"detail": "Express Shipping Place has been deleted!"},
#             status=status.HTTP_200_OK,
#         )


# class CreateStandardShippingPlace(ListCreateAPIView):
#     serializer_class = AdminStandardFreeDeliverySerializer
#     permission_classes = [
#         IsAuthenticated,
#         IsAdminUser,
#     ]

#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(
#             {"message": "Standard free Shipping Place created"},
#             status=status.HTTP_201_CREATED,
#         )

#     def get(self, request, *args, **kwargs):
#         queryset = StandardFreeDeliveryPlace.objects.all()
#         serializer = self.serializer_class(queryset, many=True)
#         return Response({"data": serializer.data}, status=status.HTTP_200_OK)


# class UpdateDeleteStandardShippingPlace(RetrieveUpdateDestroyAPIView):
#     serializer_class = AdminStandardFreeDeliverySerializer
#     permission_classes = [
#         IsAuthenticated,
#         IsAdminUser,
#     ]
#     queryset = StandardFreeDeliveryPlace.objects.all()
#     lookup_field = "pk"

#     def update(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance, data=request.data, partial=True)
#         serializer.is_valid(raise_exception=True)
#         self.perform_update(serializer)
#         return Response({"detail": "Updated!"}, status=status.HTTP_200_OK)

#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         self.perform_destroy(instance)
#         return Response(
#             {"detail": "Standard Shipping Place has been deleted!"},
#             status=status.HTTP_200_OK,
#         )


class CreateExpresshippingCharge(ListCreateAPIView):
    serializer_class = AdminExpressShippingChargeSerializer
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Express Shipping Charge created"},
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, *args, **kwargs):
        queryset = ExpressShippingCharge.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class UpdateExpressShippingCharge(UpdateAPIView):
    serializer_class = AdminExpressShippingChargeSerializer
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def update(self, request, *args, **kwargs):
        instance = ExpressShippingCharge.objects.all().first()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"detail": "Updated!"}, status=status.HTTP_200_OK)


class ViewTopBuyer(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    @extend_schema(
        operation_id="Top Buyer",
        description="""
            Allows to view top thirty buyer
            period values: weekly, montly, yearly
        """,
        parameters=[
            OpenApiParameter(
                name="period",
                required=True,
                type=str,
                description="Time Period",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        period = request.query_params.get("period", "weekly").lower()

        now = timezone.now()
        if period == "weekly":
            start_date = now - timedelta(weeks=1)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
        elif period == "yearly":
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(weeks=1)  # default to weekly

        top_buyers = (
            Orders.objects.filter(order_date__gte=start_date)
            .values("order_by")
            .annotate(total_products=Sum("items__quantity"))
            .order_by("-total_products")[:30]
        )

        top_buyers_data = []
        for buyer in top_buyers:
            user_id = buyer["order_by"]
            total_products = buyer["total_products"]

            # Get user email
            user_email = User.objects.get(id=user_id).email

            # Get products bought by this user within the specified period
            items_bought = Items.objects.filter(
                current_order=True,
                user_id=user_id,
                current_order__order_date__range=[start_date, now],
            ).select_related("item__product_variations__product")

            products_bought = []
            for item in items_bought:
                product_variation = item.item.product_variations
                product = product_variation.product
                products_bought.append(
                    {
                        "product_name": product.product_name,
                        "product_price": product_variation.product_price,
                        "quantity": item.quantity,
                    }
                )

            top_buyers_data.append(
                {
                    "user_id": user_id,
                    "total_products": total_products,
                    "user_email": user_email,
                    "products_bought": products_bought,
                }
            )

        return Response(top_buyers_data)
