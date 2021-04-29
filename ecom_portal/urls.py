from django.urls import path, include
from .views import HomeView, VendorView, VendorSignUpView, AboutView, stripe_webhook, StripeConnect, SupportView, ItemView, OrderSummaryView, PastOrderView, PaymentView, SuccessPaymentView, FailurePaymentView, Profile, add_to_cart, remove_from_cart, remove_item_from_cart, upload, email_all, SSLVerifyView
from django.views.generic import TemplateView
app_name = 'ecom_portal'
urlpatterns = [
#    path('.well-known/pki-validation/10FF0C487DEB1E6FD604967316D94A51.txt', SSLVerifyView.as_view(), name='ssl-verify'),
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('support/', SupportView.as_view(), name='support'),
    path('webhook', stripe_webhook, name = 'webhook'),
    path('order-summary/', OrderSummaryView.as_view(),name='order-summary'),
    path('payment/', PaymentView.as_view(), name='payment'),
    path('success/', SuccessPaymentView.as_view(), name='success'),
    path('failure/', FailurePaymentView.as_view(), name='failure'),
    path('accounts/orders/<pk>/', PastOrderView.as_view(), name='past-order'),
    path('accounts/profile/', Profile.as_view(), name='profile'),
    path('accounts/vendor_sign_up/', VendorSignUpView.as_view(), name='vendor_sign_up'), 
    path('accounts/profile/stripe-connect', StripeConnect.as_view(), name='stripe-connect'),
    path('<str:vendor>/add-to-cart/<slug>', add_to_cart, name='add-to-cart'),
    path('email_all', email_all, name='email_all'),
    path('<str:vendor>/remove-from-cart/<slug>', remove_from_cart, name='remove-from-cart'),
    path('<str:vendor>/remove-item-from-cart/<slug>', remove_item_from_cart, name='remove-item-from-cart'),
    path('<str:vendor>/product/<slug>/', ItemView.as_view(), name='product'),
    path('<str:vendor>/', VendorView.as_view(), name='vendor'),
]
