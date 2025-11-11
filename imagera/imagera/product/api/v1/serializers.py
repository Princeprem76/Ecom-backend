from rest_framework import serializers
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from imagera.core.payment_gateway import EsewaTransaction, KhaltiTransaction
from imagera.product.models import (
    BrandDetails,
    BusinessProductDetails,
    Category,
    ComboDiscount,
    CommentReply,
    ExtraAtrributeFields,
    LaptopProduct,
    ProductComment,
    ProductImage,
    ProductReviewRating,
    ProductTags,
    ProductVariations,
    Products,
    ReviewImages,
    SearchedProduct,
    SubCategory,
    Wishlist,
)
from datetime import timedelta, time, datetime


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class ViewCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "category_name",
            "category_image",
            "slug",
            "is_discount_active",
            "discount_start_date",
            "discount_end_date",
            "description",
        ]


class ViewSubCategorySerializer(serializers.ModelSerializer):
    sub_categories = RecursiveField(many=True, read_only=True)

    class Meta:
        model = SubCategory
        fields = [
            "id",
            "sub_category_name",
            "sub_category_discount",
            "discount_start_date",
            "discount_end_date",
            "sub_category_image",
            "is_discount_active",
            "sub_categories",
            "slug",
        ]


class ViewCategorySubCategorySerializer(serializers.ModelSerializer):
    sub_category = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "sub_category",
            "category_name",
            "category_discount",
            "discount_start_date",
            "discount_end_date",
            "slug",
            "is_discount_active",
        ]

    def get_sub_category(self, obj):
        subcategories = obj.sub_category.filter(parent_sub_category__isnull=True)
        return ViewSubCategorySerializer(
            subcategories, many=True, context=self.context
        ).data


class ViewSaleCategorySubCategorySerializer(serializers.ModelSerializer):
    sub_category = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "sub_category",
            "category_name",
            "category_discount",
            "discount_start_date",
            "discount_end_date",
            "slug",
            "is_discount_active",
        ]

    def get_sub_category(self, obj):
        now = timezone.now()
        subcategories = obj.sub_category.filter(
            Q(discount_start_date__lte=now),
            Q(discount_end_date__gte=now),
        )
        return ViewSubCategorySerializer(subcategories, many=True).data


class ProductImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "product_image"]


class LaptopProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaptopProduct
        fields = [
            "laptop_processor",
            "ram",
            "ssd",
            "hard_disk",
            "graphics_card",
            "screen_size",
            "battery_life",
            "weight",
            "operating_system",
            "others",
        ]


class ExtraAttributesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraAtrributeFields
        fields = [
            "id",
            "attribute_name",
            "attribute_value",
        ]


class ProductVariationSerializer(serializers.ModelSerializer):
    product_images = ProductImagesSerializer(many=True, read_only=True)
    stock = serializers.SerializerMethodField("get_product_quantity")
    laptop_product = LaptopProductsSerializer(read_only=True)

    class Meta:
        model = ProductVariations
        fields = [
            "id",
            "product_color",
            "product_size",
            "product_price",
            "product_images",
            "get_image_count",
            "product_weight",
            "stock",
            "laptop_product",
            "get_discounted_price",
            "slug",
        ]
        read_only_fields = ["get_image_count"]

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
        representation["extra_fields"] = ExtraAttributesSerializer(
            instance.product_extra_attribute.all(), many=True, context=self.context
        ).data

        return representation


class BusinessProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProductDetails
        fields = [
            "minimum_bulk_quantity",
            "business_discount",
        ]


class ProductBrandViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandDetails
        fields = [
            "brand_name",
            "brand_image",
            "slug",
        ]


class ProductCategoryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "category_name",
            "category_image",
            "slug",
            "is_discount_active",
            "discount_start_date",
            "discount_end_date",
        ]


class ProductsTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTags
        fields = [
            "product_tag",
        ]


class ProductSerializer(serializers.ModelSerializer):
    product_variations = ProductVariationSerializer(many=True, read_only=True)
    business_product = BusinessProductsSerializer(read_only=True)
    product_category = ProductCategoryViewSerializer(many=False, read_only=True)
    sub_category = ViewSubCategorySerializer(many=False, read_only=True)
    brand = ProductBrandViewSerializer(read_only=True)
    tag = ProductsTagSerializer(read_only=True)

    class Meta:
        model = Products
        fields = [
            "id",
            "product_name",
            "product_description",
            "product_discount",
            "product_category",
            "sub_category",
            "is_top_selling",
            "weekly_drop",
            "exciting_deals",
            "featured_product",
            "faq",
            "brand",
            "product_variations",
            "business_product",
            "age_restriction",
            "get_rating_info",
            "handpicked",
            "free_delivery",
            "best_seller",
            "slug",
            "tag",
            "has_cashback",
            "excitingdeal_start_date",
            "excitingdeal_end_date",
        ]
        read_only_fields = ["get_rating_info"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get("request", None)

        if request and hasattr(request, "user") and request.user.is_authenticated:
            user = request.user
            if user.user_type != 4:
                representation.pop("business_product", None)
            if user.user_type != 2:
                SearchedProduct.objects.get_or_create(user=user, product=instance)
        else:
            representation.pop("business_product", None)
        representation["min_price"] = self.get_min_discounted_price(instance)
        representation["product_variations"] = ProductVariationSerializer(
            instance.product_variations.all(), many=True, context=self.context
        ).data
        delivery_start = None
        delivery_end = None
        start_time = time(10, 0)  # 10 AM
        end_time = time(18, 0)  # 6 PM

        current_time = datetime.now()
        order_time = current_time.time()

        if start_time <= order_time <= end_time:
            additional_hours = 12
        else:
            additional_hours = 18

        if current_time.weekday() == 5:  # If today is Saturday (returns 5)
            additional_hours += 24

        representation["delivery_by"] = [
            {
                "Normal": [
                    {"delivery_start": current_time + timedelta(hours=24)},
                    {"delivery_end": current_time + timedelta(hours=72)},
                ]
            },
            {
                "Express": [
                    {
                        "delivery_start": current_time
                        + timedelta(hours=additional_hours)
                    },
                    {
                        "delivery_end": current_time
                        + timedelta(hours=additional_hours + 2)
                    },
                ]
            },
        ]
        return representation

    def get_min_discounted_price(self, obj):
        # Calculate the minimum discounted price among the product variants
        min_price = float("inf")
        distinct_prices = set()

        for variant in obj.product_variations.all():
            base_price = variant.get_discounted_price()
            distinct_prices.add(base_price["final_price"])

        if distinct_prices:
            min_price = min(distinct_prices)

        return min_price if min_price != float("inf") else None


class ProductReplySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = CommentReply
        fields = [
            "content",
            "username",
            "created_at",
        ]

    def get_username(self, obj):
        return obj.user.name


class ProductCommentSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(max_length=255, write_only=True)
    username = serializers.SerializerMethodField("get_username")
    reply = serializers.SerializerMethodField("get_replies")

    class Meta:
        model = ProductComment
        fields = [
            "content",
            "username",
            "product_id",
            "reply",
            "created_at",
        ]

    def get_username(self, obj):
        return obj.user.name

    def create(self, validated_data):
        comment = ProductComment.objects.create(
            user=self.context["request"].user, **validated_data
        )
        return validated_data

    def get_replies(self, obj):
        reply = CommentReply.objects.filter(comment_id=obj.id)
        serializer = ProductReplySerializer(reply, many=True)
        return serializer.data


class WishlistSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "products"]


class ReviewProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImages
        fields = ["id", "image"]


class ProductReviewRatingSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField("get_username")
    product_id = serializers.CharField(max_length=255, write_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(write_only=True, required=False),
        write_only=True,
        required=False,
    )

    class Meta:
        model = ProductReviewRating
        fields = ["id", "username", "review", "rating", "uploaded_images", "product_id"]

    def get_username(self, obj):
        return obj.user.name

    def create(self, validated_data):
        product_id = validated_data.pop("product_id")
        images = validated_data.pop("uploaded_images", [])
        review = ProductReviewRating.objects.create(
            user=self.context["request"].user, product_id=product_id, **validated_data
        )
        for img in images:
            ReviewImages.objects.create(review=review, image=img)
        return validated_data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["images"] = ReviewProductImageSerializer(
            instance.review_images.all(), many=True, context=self.context
        ).data
        return representation

class ImageSearchRequestSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)

    def validate(self, attrs):
        if not attrs.get("image"):
            raise serializers.ValidationError("Provide image.")
        return attrs