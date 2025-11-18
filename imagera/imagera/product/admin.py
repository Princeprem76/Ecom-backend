from django.contrib import admin

from imagera.product.models import (
    Category,
    ComboDiscount,
    Products,
    SubCategory,
    LaptopProduct,
    ProductVariations,
    ProductImage,
    ProductComment,
    CommentReply,
    ProductReviewRating,
    SearchedProduct,
    ExtraAtrributeFields,
    ProductTags,
    BrandDetails,
)
from django_summernote.admin import SummernoteModelAdmin


class ProductFaqAdmin(SummernoteModelAdmin):
    summernote_fields = ('faq',)


# Register your models here.
admin.site.register(Products, ProductFaqAdmin)
admin.site.register(
    [
        Category,
        SubCategory,
        ComboDiscount,
        LaptopProduct,
        ProductVariations,
        ProductImage,
        ProductReviewRating,
        ProductComment,
        CommentReply,
        SearchedProduct,
        ExtraAtrributeFields,
        ProductTags,
        BrandDetails,
    ]
)
