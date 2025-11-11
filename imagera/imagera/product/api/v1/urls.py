from django.urls import path
from rest_framework.routers import DefaultRouter

from imagera.product.api.v1.views import (
    # AddUsersSubscription,
    CategoryRecommendationView,
    # ComboDiscountInCartView,
    CreateProductReviewRating,
    CreateViewWishItem,
    FindProducts,
    ForbiddenDeliveryCheck,
    ImageFindProducts,
    ProductCommentView,
    ProductComparisonView,
    ProductRecommendationView,
    RemoveItemFromWishlist,
    SingleProductView,
    # SubscriptionPlanList,
    TopProductSoldList,
    TopReviewRating,
    TopSellingProductView,
    ViewCategory,
    ViewCategorySubCategory,
    # ViewComboProducts,
    ViewSaleCategory,
    ViewSaleCategorySubCategory,
    ViewSaleProducts,
    ViewSubCategory,
    ExcitingDealsProductView,
    WeeklyDropProductView,
    FeaturedProductView,
)


app_name = "product"

router = DefaultRouter()

urlpatterns = [
    path(
        "category-view/",
        ViewCategory.as_view(),
        name="view_category",
    ),
    path(
        "subcategory-view/",
        ViewSubCategory.as_view(),
        name="view_subcategory",
    ),
    path(
        "category-subcategory-view/",
        ViewCategorySubCategory.as_view(),
        name="category_subcategory_view",
    ),
    path(
        "sale-category-view/",
        ViewSaleCategory.as_view(),
        name="category_sale_view",
    ),
    path(
        "sale-category-subcategory-view/",
        ViewSaleCategorySubCategory.as_view(),
        name="category_subcategory_sale_view",
    ),
    path(
        "sale-product-view/",
        ViewSaleProducts.as_view(),
        name="product_sale_view",
    ),
    path(
        "search-product-view/",
        FindProducts.as_view(),
        name="product_search_view",
    ),
    path(
        "product-view/",
        SingleProductView.as_view(),
        name="single_product_view",
    ),
    path(
        "wishlist/",
        CreateViewWishItem.as_view(),
        name="wishlist_create_view",
    ),
    path(
        "remove-wishlist/",
        RemoveItemFromWishlist.as_view(),
        name="remove_item_wishlist",
    ),
    path(
        "add-query/",
        ProductCommentView.as_view(),
        name="product_query",
    ),
    path(
        "product-rating/",
        CreateProductReviewRating.as_view(),
        name="product_rating",
    ),
    path(
        "product-compare/",
        ProductComparisonView.as_view(),
        name="product_compare",
    ),
    path(
        "top-selling/",
        TopSellingProductView.as_view(),
        name="top_selling",
    ),
    # path(
    #     "view-comboproduct/",
    #     ViewComboProducts.as_view(),
    #     name="combo_product",
    # ),
    # path(
    #     "cart-combo-discount-item/",
    #     ComboDiscountInCartView.as_view(),
    #     name="cart_combo_discount_product",
    # ),
    path(
        "check-forbidden-delivery/<str:product_name>/<str:district>/",
        ForbiddenDeliveryCheck.as_view(),
        name="check_forbidden_delivery",
    ),
    path(
        "most-sold-product/",
        TopProductSoldList.as_view(),
        name="most_sold_product",
    ),
    path(
        "recommendation/",
        ProductRecommendationView.as_view(),
        name="product_recommendation",
    ),
    path(
        "category-recommendation/",
        CategoryRecommendationView.as_view(),
        name="category_recommendation",
    ),
    path(
        "exciting-deals/",
        ExcitingDealsProductView.as_view(),
        name="exciting_deals_product",
    ),
    path(
        "weekly-drops/",
        WeeklyDropProductView.as_view(),
        name="weekly_drop_product",
    ),
    path(
        "featured-product/",
        FeaturedProductView.as_view(),
        name="featured_product",
    ),
    path(
        "top-review/",
        TopReviewRating.as_view(),
        name="top_review_rating",
    ),
    path(
        "search/image/",
        ImageFindProducts.as_view(),
        name="product-image-search",
    ),
]


urlpatterns += router.urls
