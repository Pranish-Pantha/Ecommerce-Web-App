from django.contrib import admin
from django.urls import path
from django.contrib.admin.options import InlineModelAdmin
from .models import UserProfile, Item, VendorProfile , OrderItem, Order, OrderConfirmation
from django.shortcuts import reverse
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe
from .views import email_all, custom_transfer
from django.contrib import messages
from django.utils.translation import ngettext
from django.core import mail
from django.utils.html import format_html
import stripe
from django.middleware.csrf import get_token
stripe.api_key = "" # Stripe key
from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent
fee = 0.05
class VendorAdminSite(admin.AdminSite):
    site_header = "Vendors"
    site_title = "Vendors Title"
    index_title = "Index Vendors Title"

    def has_permission(self, request):
        if request.user.id is None:
            return False
        return True
class VendorProfileAdmin(admin.ModelAdmin):
    change_list_template = 'custom_transfer.html'
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('custom_transfer/', custom_transfer),
        ]
        return my_urls + urls
    exclude = ('latitude','longitude')
    actions = ['make_approved', 'transfer_owed']
    search_fields = ('stripe_id',)
    list_display = ( 'VendorProfile', 'latitude', 'longitude', 'Payment_Owed')
    def Payment_Owed(self, obj):
        return obj.payment_owed
    def transfer_owed(self, request, queryset):
        for vendor in queryset:
            amount = int(100*vendor.payment_owed*(1-fee))
            transfer = stripe.Transfer.create(
            amount=amount,
            currency='usd',
            destination=vendor.stripe_id)
            vendor.payment_owed = 0
            vendor.save()

    def make_approved(self, request, queryset):
        vendor_group = Group.objects.get(name='Vendors')
        for vendor in queryset:
            user = vendor.user
            user.groups.add(vendor_group)
            user.save()
        updated = queryset.update(approved=True)
        self.message_user(request, ngettext(
            '%d vendor was approved.',
            '%d vendors were approved.',
            updated,
        ) % updated, messages.SUCCESS)
    def VendorProfile(self, obj):
        return obj
class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ('stripe_id',)
    change_list_template = 'email_all.html'
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('email_all/', email_all),
        ]
        return my_urls + urls

class ItemAdmin(admin.ModelAdmin):
    exclude = ('vendor','slug')
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(vendor=VendorProfile.objects.get(approved=True, user=request.user))
    def save_model(self, request, obj, form, change):
        obj.vendor = VendorProfile.objects.get(approved=True, user=request.user)
        super().save_model(request, obj, form, change)
class OrderConfirmationAdmin(admin.ModelAdmin):
    actions = ['make_picked_up']
    def make_picked_up(self, request, queryset):
        queryset.update(picked_up=True)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(vendor=VendorProfile.objects.get(approved=True, user=request.user))
class OrderAdmin(admin.ModelAdmin):
    list_display = ( 'Order', 'user_link', 'order_id')
    filter_horizontal = ('items',)
    search_fields = ('order_id',)
    actions = ["make_ordered", "make_picked_up"]
    
    def make_ordered(self, request, queryset):
        queryset.update(ordered=True)
    # inlines = ['items']
    def make_picked_up(self, request, queryset):
        queryset.upadte(picked_up=True)
    def Order(self, obj):
        return "Order"
        # return "\n".join([str(item) for item in obj.items.all()])
    def order_id(self,obj):
        return obj.order_id
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        link = '<a href="%s">%s</a>' % (url, obj.user.last_name)
        return mark_safe(link)
    user_link.short_description = 'User'
vendor_admin_site = VendorAdminSite(name='vendor_admin')
vendor_admin_site.register(Item, ItemAdmin)
vendor_admin_site.register(OrderConfirmation, OrderConfirmationAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(VendorProfile, VendorProfileAdmin)
admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderConfirmation)
