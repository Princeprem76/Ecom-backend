from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from config.settings.base import env
from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
)
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from imagera.core.pagination import DynamicPageNumberPagination
from django.db.models import Avg, Count
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from imagera.core.recommendations import get_hybrid_recommendations
from imagera.orders.models import ForbiddenDelivery, Items
from imagera.product.api.v1.serializers import (
    ImageSearchRequestSerializer,
    ProductCommentSerializer,
    ProductReviewRatingSerializer,
    ProductSerializer,
    ViewCategorySerializer,
    ViewCategorySubCategorySerializer,
    ViewSaleCategorySubCategorySerializer,
    ViewSubCategorySerializer,
    WishlistSerializer,
)
from imagera.product.models import (
    Category,
    ComboDiscount,
    ExtraAtrributeFields,
    ProductComment,
    ProductReviewRating,
    ProductVariations,
    Products,
    RemovedFromCart,
    SearchedProduct,
    SubCategory,
    WishItem,
    Wishlist,
)
from django.utils import timezone
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
import json
from django.core.cache import cache
from core.bing_search_service import ImageProductSearch

class ViewCategory(ListAPIView):
    permission_classes = []
    serializer_class = ViewCategorySerializer
    queryset = Category.objects.all()

    @extend_schema(
        operation_id="Category Search",
        description="""
            Allows to view and search category.
        """,
        parameters=[
            OpenApiParameter(
                name="slug",
                required=False,
                type=str,
                description="slug of category",
            ),
        ],
    )
    def get_queryset(self):
        queryset = Category.objects.all()
        slug = self.request.query_params.get("slug", None)
        if slug:
            queryset = queryset.filter(slug=slug)
        return queryset


class ViewSubCategory(ListAPIView):
    permission_classes = []
    serializer_class = ViewSubCategorySerializer
    queryset = SubCategory.objects.all()

    @extend_schema(
        operation_id="Sub Category Search",
        description="""
            Allows to view and search sub category.
        """,
        parameters=[
            OpenApiParameter(
                name="slug",
                required=False,
                type=str,
                description="slug of subcategory",
            ),
        ],
    )
    def get_queryset(self):
        queryset = SubCategory.objects.all()
        slug = self.request.query_params.get("slug", None)
        if slug:
            queryset = queryset.filter(slug=slug)
        return queryset


class ViewCategorySubCategory(ListAPIView):
    permission_classes = []
    serializer_class = ViewCategorySubCategorySerializer
    queryset = Category.objects.all()


class ViewSaleCategory(ListAPIView):
    permission_classes = []
    serializer_class = ViewCategorySerializer
    queryset = Category.objects.all()

    def get_queryset(self):
        now = timezone.now()
        return Category.objects.filter(
            Q(discount_start_date__lte=now),
            Q(discount_end_date__gte=now),
        )


class ViewSaleCategorySubCategory(ListAPIView):
    permission_classes = []
    serializer_class = ViewSaleCategorySubCategorySerializer
    queryset = Category.objects.all()

    def get_queryset(self):
        now = timezone.now()
        # Filter categories with active discounts
        categories_with_active_discounts = Category.objects.filter(
            Q(discount_start_date__lte=now),
            Q(discount_end_date__gte=now),
        )

        # Filter categories that have subcategories with active discounts
        categories_with_active_subcategory_discounts = Category.objects.filter(
            sub_category__discount_start_date__lte=now
        ) & Category.objects.filter(sub_category__discount_end_date__gte=now)

        return (
            categories_with_active_discounts
            | categories_with_active_subcategory_discounts
        ).distinct()


class ViewSaleProducts(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        now = timezone.now()
        # Filter products with active discounts
        products_with_active_discounts = Products.objects.filter(
            Q(product_discount__gt=0)
        )

        # Filter products that belong to categories with active discounts
        products_with_active_category_discounts = Products.objects.filter(
            product_category__discount_start_date__lte=now
        ) & Products.objects.filter(product_category__discount_end_date__gte=now)

        # Filter products that belong to subcategories with active discounts
        products_with_active_subcategory_discounts = Products.objects.filter(
            sub_category__discount_start_date__lte=now
        ) & Products.objects.filter(sub_category__discount_end_date__gte=now)

        # Combine all filters
        combined_queryset = (
            products_with_active_discounts
            | products_with_active_category_discounts
            | products_with_active_subcategory_discounts
        ).distinct()

        return combined_queryset

    def get_brands(self, queryset):
        return queryset.values_list("brand_name", flat=True).distinct()

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            brands = self.get_brands(queryset)
            response_data = {
                "data": serializer.data,
                "brands": list(brands),  # Convert queryset to list
            }
            return self.get_paginated_response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        brands = self.get_brands(queryset)
        response_data = {
            "data": serializer.data,
            "brands": list(brands),  # Convert queryset to list
        }
        return Response(response_data, status=status.HTTP_200_OK)


class FindProducts(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        queryset = Products.objects.all()

        all_product = self.request.query_params.get("products", None)
        user = self.request.user if self.request.user.is_authenticated else None
        search_vector = (
            SearchVector("product_name", weight="A")
            + SearchVector("product_category__category_name", weight="B")
            + SearchVector("sub_category__sub_category_name", weight="B")
            + SearchVector("brand__brand_name", weight="C")
        )
        if all_product:
            if user:
                SearchedProduct.objects.get_or_create(
                    user=user, searched_term=all_product
                )

            search_query = SearchQuery(all_product)
            queryset = (
                queryset.annotate(rank=SearchRank(search_vector, search_query))
                .filter(rank__gte=0.1)
                .order_by("-rank")
            )
        # Filter by product name
        product_names = self.request.query_params.get("product_name", None)
        if product_names:
            if user:
                SearchedProduct.objects.get_or_create(
                    user=user, searched_term=product_names
                )
            product_name_query = SearchQuery(product_names)
            queryset = (
                queryset.annotate(rank=SearchRank(search_vector, product_name_query))
                .filter(rank__gte=0.3)
                .order_by("-rank")
            )

        # Filter by category
        product_category = self.request.query_params.get("category", None)
        if product_category:
            if user:
                SearchedProduct.objects.get_or_create(
                    user=user, searched_term=product_category
                )
            queryset = queryset.filter(
                Q(product_category__category_name__iexact=product_category)
                | Q(sub_category__sub_category_name__iexact=product_category)
                | Q(
                    sub_category__parent_sub_category__sub_category_name__iexact=product_category
                )
            ).distinct()

        # Filter by brand
        product_brands = self.request.query_params.getlist("brand", None)
        if product_brands:
            brand_filter = Q()
            for brand in product_brands:
                brand_filter |= Q(brand__brand_name__iexact=brand)
            queryset = queryset.filter(brand_filter)
        attribute = self.request.query_params.getlist("attributes", None)
        if attribute:
            try:
                # Parse the attributes JSON
                attribute = serializers.JSONField().to_internal_value(attribute)
                attribute_filter = Q()
                for attr in attribute:
                    name, value = json.loads(attr)
                    if name and value:
                        attribute_filter |= Q(
                            product_variations__product_extra_attribute__attribute_name=name,
                            product_variations__product_extra_attribute__attribute_value=value,
                        )
                queryset = queryset.filter(attribute_filter).distinct()
            except ValueError:
                pass  # Handle invalid JSON input

        # Filter by price range
        min_price = self.request.query_params.get("min_price", None)
        max_price = self.request.query_params.get("max_price", None)
        if min_price and max_price:
            queryset = queryset.filter(
                product_variations__product_price__gte=min_price,
                product_variations__product_price__lte=max_price,
            )
        delivery_free = self.request.query_params.get("free_delivery", None)
        if delivery_free:
            queryset = queryset.filter(delivery_free=True)
        handpicked = self.request.query_params.get("handpicked", None)
        if handpicked:
            queryset = queryset.filter(handpicked=True)

        instock = self.request.query_params.get("in_stock", None)
        if instock:
            queryset = queryset.filter(product_variations__product_quantity__gte=1)

        ratings = self.request.query_params.get("ratings", None)
        if ratings:
            queryset = queryset.annotate(
                average_rating=Avg("product_rating__rating")
            ).filter(average_rating__gte=ratings)

        if user and self.request.user.age() < 18:
            queryset = queryset.filter(age_restriction=False)

        return queryset

    def get_brands(self, queryset):
        return queryset.values_list("brand_name", flat=True).distinct()

    @extend_schema(
        operation_id="Product Search API",
        description="""
            Allows to search product.
        """,
        parameters=[
            OpenApiParameter(
                name="products",
                required=False,
                type=str,
                description="to search product in all category, brand and product name",
            ),
            OpenApiParameter(
                name="product_name",
                required=False,
                type=str,
                description="name of respected product",
            ),
            OpenApiParameter(
                name="category",
                required=False,
                type=str,
                description="category name on which product is to be searched",
            ),
            OpenApiParameter(
                name="brand",
                required=False,
                type={"type": "array", "items": {"type": "string"}},
                description="brand name",
            ),
            OpenApiParameter(
                name="attributes",
                required=False,
                type={
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": [
                            {"type": "string", "description": "Attribute Name"},
                            {"type": "string", "description": "Attribute Value"},
                        ],
                    },
                },
                description="attribute name",
            ),
            OpenApiParameter(
                name="free_delivery",
                required=False,
                type=bool,
                description="Free Delivery",
            ),
            OpenApiParameter(
                name="handpicked",
                required=False,
                type=bool,
                description="Mountemart handpicked",
            ),
            OpenApiParameter(
                name="in_stock",
                required=False,
                type=bool,
                description="In Stock",
            ),
            OpenApiParameter(
                name="min_price",
                required=False,
                type=str,
                description="minimum price",
            ),
            OpenApiParameter(
                name="max_price",
                required=False,
                type=str,
                description="maximum price",
            ),
            OpenApiParameter(
                name="ratings",
                required=False,
                type=str,
                description="ratings",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        brands = self.get_brands(queryset)

        # Filter the ProductVariations based on the given queryset
        product_variations = ProductVariations.objects.filter(product__in=queryset)
        attribute_fields = ExtraAtrributeFields.objects.filter(
            variation__in=product_variations
        )
        attributes = attribute_fields.values("attribute_name").distinct()
        attribute_values = {}

        for attribute in attributes:
            name = attribute["attribute_name"]
            values = list(
                attribute_fields.filter(attribute_name=name)
                .values_list("attribute_value", flat=True)
                .distinct()
            )
            attribute_values[name] = values

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = {
                "data": serializer.data,
                "brands": list(brands),  # Convert queryset to list
                "attributes": attribute_values,  # Include the attribute values in the response
            }
            return self.get_paginated_response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            "data": serializer.data,
            "brands": list(brands),  # Convert queryset to list
            "attributes": attribute_values,  # Include the attribute values in the response
        }
        return Response(response_data, status=status.HTTP_200_OK)


class SingleProductView(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer

    @extend_schema(
        operation_id="Individual Product Search API",
        description="""
            Allows to individual product.
        """,
        parameters=[
            OpenApiParameter(
                name="id",
                required=False,
                type=str,
                description="search by product id",
            ),
            OpenApiParameter(
                name="slug",
                required=False,
                type=str,
                description="search by slug",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        product_id = self.request.query_params.get("id", None)
        product_slug = self.request.query_params.get("slug", None)
        if product_id:
            product_data = Products.objects.get(id=product_id)
        else:
            product_data = Products.objects.get(slug=product_slug)
        serializer = ProductSerializer(product_data, many=False)
        comment = ProductComment.objects.filter(product_id=product_id).order_by(
            "-created_at"
        )
        comment_serializer = ProductCommentSerializer(comment, many=True)
        rating = ProductReviewRating.objects.filter(product_id=product_id)
        rating_serializer = ProductReviewRatingSerializer(rating, many=True)
        response = {
            "data": serializer.data,
            "comment": comment_serializer.data,
            "rating": rating_serializer.data,
        }
        return Response(response, status=status.HTTP_200_OK)


class TopSellingProductView(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        query_set = Products.objects.filter(is_top_selling=True)
        if (
            self.request
            and hasattr(self.request, "user")
            and self.request.user.is_authenticated
            and self.request.user.age() < 18
        ):
            query_set = query_set.filter(age_restriction=False)

        return query_set

    def get(self, request, *args, **kwargs):
        product_data = self.get_queryset()
        serializer = ProductSerializer(product_data, many=True)
        response = {"data": serializer.data}
        return Response(response, status=status.HTTP_200_OK)


class ProductCommentView(CreateAPIView):
    permission_classes = [
        IsAuthenticated,
    ]
    serializer_class = ProductCommentSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Query Posted!"}, status=status.HTTP_201_CREATED)


class CreateViewWishItem(ListCreateAPIView):
    permission_classes = [
        IsAuthenticated,
    ]
    pagination_class = PageNumberPagination
    serializer_class = WishlistSerializer

    @extend_schema(
        operation_id="Wish List Create API",
        description="""
            Allows to add item from wishlist.
        """,
        parameters=[
            OpenApiParameter(
                name="id",
                required=True,
                type=str,
                description="Id of respected product",
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        try:
            ids = request.query_params.get("id")
            item = get_object_or_404(Products, id=ids)
            ord, created = WishItem.objects.get_or_create(item=item)
            order_qs = Wishlist.objects.filter(user=request.user)
            if order_qs.exists():
                order = order_qs[0]
                if order.products.filter(item=item).exists():
                    return Response(
                        {"message": "Product already added to wishlist"},
                        status=status.HTTP_208_ALREADY_REPORTED,
                    )
                else:
                    order.products.add(ord)
                    return Response(
                        {"message": "Product added to wishlist"},
                        status=status.HTTP_202_ACCEPTED,
                    )
            else:
                order = Wishlist.objects.create(user=request.user)
                order.products.add(ord)
                return Response(
                    {"message": "Product added to wishlist"},
                    status=status.HTTP_202_ACCEPTED,
                )
        except:
            return Response(
                {"message": "Product not found!"}, status=status.HTTP_204_NO_CONTENT
            )

    def get(self, request, *args, **kwargs):
        try:
            data = Wishlist.objects.filter(user=request.user)
            serializer = WishlistSerializer(data, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except:
            return Response(
                {"message": "No item in wish list!"}, status=status.HTTP_400_BAD_REQUEST
            )


class RemoveItemFromWishlist(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="Wish List Remove API",
        description="""
            Allows to remove item from wishlist.
        """,
        parameters=[
            OpenApiParameter(
                name="id",
                required=True,
                type=str,
                description="Id of respected product",
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        try:
            ids = request.query_params.get("id")
            item = get_object_or_404(Products, id=ids)
            order_qs = Wishlist.objects.filter(
                user=request.user,
            )
            if order_qs.exists():
                order = order_qs[0]
                if order.products.filter(item=item).exists():
                    order_item = WishItem.objects.filter(
                        item=item,
                    )[0]
                    order.products.remove(order_item)
                    RemovedFromCart.objects.create(user=request.user, product_id=ids)
                    return Response(
                        {"message": "The wishlist is updated!"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"message": "error"}, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {"message": "You do not have an active wishlist"},
                    status=status.HTTP_204_NO_CONTENT,
                )
        except:
            return Response(
                {"message": "Product not found!"}, status=status.HTTP_204_NO_CONTENT
            )


class CreateProductReviewRating(CreateAPIView):
    serializer_class = ProductReviewRatingSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Review added successfully"}, status=status.HTTP_201_CREATED
        )


class TopReviewRating(ListAPIView):
    serializer_class = ProductReviewRatingSerializer
    permission_classes = []

    @extend_schema(
        operation_id="Product Top Review",
        description="""
            Allows to get product top review.
        """,
        parameters=[
            OpenApiParameter(
                name="product_id",
                required=True,
                type=str,
                description="Id of respected product",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        product_id = request.query_params.get("product_id")
        queryset = ProductReviewRating.objects.filter(
            product_id=product_id, top_review=True
        )
        serializer = self.serializer_class(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class ProductComparisonView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = []
    queryset = Products.objects.all()

    @extend_schema(
        operation_id="Product Compare API",
        description="""
            Allows to get data of compared products.
        """,
        parameters=[
            OpenApiParameter(
                name="product_ids",
                location=OpenApiParameter.QUERY,
                required=True,
                type={"type": "array", "items": {"type": "integer"}},
                description="Id of respected product",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        product_ids = request.query_params.getlist("product_ids")
        products = Products.objects.filter(id__in=product_ids)
        serializer = ProductSerializer(products, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)



class ForbiddenDeliveryCheck(ListAPIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        product_name = kwargs.get("product_name")
        district = kwargs.get("district")
        forbidden_delivery = ForbiddenDelivery.objects.filter(
            product__product_name__icontains=product_name, district__iexact=district
        ).exists()
        if forbidden_delivery:
            response = f"Sorry, we do not deliver {product_name} to {district}."
        else:
            response = f"Yes, we can deliver {product_name} to {district}."
        return Response(response)


class ProductRecommendationView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        user_id = request.user.id if request.user.is_authenticated else None
        recommendations = get_hybrid_recommendations(user_id)
        try:
            unique_products = recommendations["id"].unique().tolist()
            product = Products.objects.filter(id__in=unique_products)
            serializer = ProductSerializer(product, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except KeyError:
            return Response(
                {"details": "No recommendation Available!"}, status=status.HTTP_200_OK
            )


class CategoryRecommendationView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        user_id = request.user.id if request.user.is_authenticated else None
        recommendations = get_hybrid_recommendations(user_id)
        unique_categories = recommendations["product_category_name"].unique().tolist()
        category = Category.objects.filter(category_name__in=unique_categories)
        category_data = ViewCategorySerializer(category, many=True).data
        return Response({"data": category_data}, status=status.HTTP_200_OK)


class TopProductSoldList(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer

    def get(self, request, *args, **kwargs):
        top_product_ids = cache.get("top_products", [])
        top_products = Products.objects.filter(id__in=top_product_ids)
        if (
            self.request
            and hasattr(self.request, "user")
            and self.request.user.is_authenticated
            and self.request.user.age() < 18
        ):
            top_products = top_products.filter(age_restriction=False)
        serializer = ProductSerializer(top_products, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


class ExcitingDealsProductView(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        query_set = Products.objects.all()
        query_set = [product for product in query_set if product.exciting_deals]
        if (
            self.request
            and hasattr(self.request, "user")
            and self.request.user.is_authenticated
            and self.request.user.age() < 18
        ):
            query_set = [product for product in query_set if not product.age_restriction]

        return query_set

    def get(self, request, *args, **kwargs):
        product_data = self.get_queryset()
        serializer = ProductSerializer(product_data, many=True)
        response = {"data": serializer.data}
        return Response(response, status=status.HTTP_200_OK)


class FeaturedProductView(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        query_set = Products.objects.filter(featured_product=True)
        if (
            self.request
            and hasattr(self.request, "user")
            and self.request.user.is_authenticated
            and self.request.user.age() < 18
        ):
            query_set = query_set.filter(age_restriction=False)

        return query_set

    def get(self, request, *args, **kwargs):
        product_data = self.get_queryset()
        serializer = ProductSerializer(product_data, many=True)
        response = {"data": serializer.data}
        return Response(response, status=status.HTTP_200_OK)


class WeeklyDropProductView(ListAPIView):
    permission_classes = []
    serializer_class = ProductSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        query_set = Products.objects.filter(weekly_drop=True)
        if (
            self.request
            and hasattr(self.request, "user")
            and self.request.user.is_authenticated
            and self.request.user.age() < 18
        ):
            query_set = query_set.filter(age_restriction=False)

        return query_set

    def get(self, request, *args, **kwargs):
        product_data = self.get_queryset()
        serializer = ProductSerializer(product_data, many=True)
        response = {"data": serializer.data}
        return Response(response, status=status.HTTP_200_OK)




class ImageFindProducts(FindProducts):
    """
    POST an image (or image_url) → use Bing Visual Search to get product name →
    inject into FindProducts as 'product_name' → return the same payload format.
    """
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser, JSONParser] 

    @extend_schema(
        operation_id="Product Image Search API",
        description="Upload an image. Extracts a product name and reuses text search.",
        request=ImageSearchRequestSerializer,           
        responses={200: ProductSerializer(many=True)},
    )
    def post(self, request, *args, **kwargs):
        image_file = request.FILES.get("image")
        

        if not image_file:
            return Response(
                {"detail": "Provide Image to process this request!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_service = ImageProductSearch(
            endpoint=getattr(env, "BING_VISUAL_SEARCH_ENDPOINT"),
            subscription_key=getattr(env, "BING_VISUAL_SEARCH_KEY"),
            market=getattr(env, "BING_MARKET", "en-US"),
        )

        product_name = image_service.extract_product_name(image_file=image_file)

        if not product_name:
            return Response(
                {"detail": "Could not extract a product name from the image."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        user = request.user if request.user.is_authenticated else None
        if user:
            SearchedProduct.objects.get_or_create(user=user, searched_term=product_name)

        mutable_qs = request._request.GET.copy() if hasattr(request._request, "GET") else QuerySet(mutable=True)
        mutable_qs["product_name"] = product_name
        request._request.GET = mutable_qs

        return super().get(request, *args, **kwargs)