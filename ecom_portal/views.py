from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.dispatch.dispatcher import receiver
from allauth.account.signals import user_logged_in
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Item, UserProfile, VendorProfile, OrderItem, Order, OrderConfirmation, CATEGORY_CHOICES
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.utils import timezone
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from myproject.settings import MEDIA_ROOT
import openpyxl
from io import BytesIO
from PIL import Image
import requests
import os
from pathlib import Path
from haversine import haversine
import uuid
import json
import ast
import stripe
BASE_DIR = Path(__file__).resolve().parent.parent
fee = 0.05
stripe.api_key = "" # Stripe key
# Home page with Map 
class HomeView(View):
    def get(self, *args, **kwargs):
        # Initializes the context that the template needs and returns a response
        context = {'vendors': [], 'Map': True, 'categories':CATEGORY_CHOICES}
        response = render(self.request, 'home-page.html', context=context)
        response.delete_cookie('items')
        return response
    def post(self, *args, **kwargs):
        # Uses HERE API to find coordinates of zip code submitted
        res = requests.get(f'https://geocode.search.hereapi.com/v1/geocode?q={self.request.POST["zip-code"]}, NC&apiKey=') # Add HERE API key
        res = json.loads(res.content)
        user_lat = res['items'][0]['position']['lat']
        user_long = res['items'][0]['position']['lng']
        # Filters the vendors based on the form
        if self.request.POST['flexRadioDefault'] == 'All':
            result = VendorProfile.objects.filter(approved=True).values()
        else:
            result = VendorProfile.objects.filter(approved=True, category=self.request.POST['flexRadioDefault']).values()
        # Finds locations that are within 100 km of the submitted location
        close_locations = []
        for entry in result:
            if haversine((user_lat, user_long), (entry['latitude'], entry['longitude'])) < 100:
                close_locations.append({'vendor_name': entry['vendor_name'],'location': entry['location'], 'latitude': entry['latitude'], 'longitude': entry['longitude']})
        context = {'Map': True, 'vendors': close_locations, 'value': self.request.POST['zip-code'],'categories':CATEGORY_CHOICES}
        return render(self.request, 'home-page.html', context=context)
# Home Page with Vendor items
class VendorView(ListView):
    model = Item
    template_name = 'home-page.html'
    paginate_by = 5

    def get_queryset(self):
        
        try:
            # Searches for the vendor and gives the list of items
            vendor = VendorProfile.objects.get(approved= True, vendor_name=self.kwargs['vendor'])
            print("ITEMS ARE", Item.objects.filter(vendor=vendor))
            return Item.objects.filter(vendor=vendor)
        except ObjectDoesNotExist:
            print("Vendor does not exist")
    def get_context_data(self, **kwargs):
        # Conext to ensure proper templating
        context = super().get_context_data(**kwargs)
        context['Map'] = False
        context['VendorPage'] = True
        context['no_search'] = True
        result = VendorProfile.objects.filter(approved = True).values()   
        context['vendors'] = [entry for entry in result]
        return context
# Form to request to become a vendor
class VendorSignUpView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        # if vendor already exists, returns to profile page
        if VendorProfile.objects.filter(approved=True, user=self.request.user).exists():
            return redirect('ecom_portal:profile')
        context = {}
        user_profile = UserProfile.objects.get(user=self.request.user)
        response = render(self.request, 'vendor_sign_up.html', context=context)
        response.delete_cookie('items')
        return response

    def post(self, *args, **kwargs):
        # Creates a vendor based on form data
        vendor = VendorProfile.objects.create(approved=False, user=self.request.user,
        vendor_name=self.request.POST['name'],
        location = self.request.POST['address'],
        zip_code = self.request.POST['zip_code'],
        category = self.request.POST['category'],
        )
        uploaded_file = self.request.FILES['logo']
        image = uploaded_file.file
        image = Image.open(image)
        image.save(MEDIA_ROOT + f'{vendor.vendor_name}_logo.png')
        vendor.logo = f'{vendor.vendor_name}_logo.png'
        vendor.save()
        return redirect('ecom_portal:profile')
# About Page
class AboutView(TemplateView):
    template_name = "about.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
# Support Page
class SupportView(View):
    def get(self,*args,**kwargs):
        context = {'support_page': True}
        return render(self.request, 'support.html', context)
    def post(self, *args, **kwargs):
        try:
            # Sends email based on form data
            subject = 'Support for ' + self.request.POST['first_name'] + " " + self.request.POST['last_name'] + '. ' + self.request.POST.get('order_id', " ") + '. ' + self.request.POST.get('location', " ")
            plain_message = 'Thank you for contacting us. Your support request was received and we will get back to you as soon as possible.\nYour message: ' + self.request.POST['message']
            from_email = 'email@gmail.com'
            to =  [self.request.POST['email'], 'email@gmail.com'] 
            mail.send_mail(subject, plain_message, from_email, to)
            messages.info(self.request, "Support email was sent.")
        except:
            messages.info(self.request, "Error in support form.")
        context = {'support_page': True}
        return render(self.request, 'support.html', context)
# Detail page for each item    
class ItemView(DetailView):
    model = Item
    template_name = 'product-page.html'
    def get_object(self):
        obj = get_object_or_404(Item, slug=self.kwargs['slug'], vendor__vendor_name=self.kwargs['vendor'])
        return obj
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
# Cart page
class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            # Gets current order if it exists, else redirects
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order,
                'past': False,
                'order_id': order.order_id,
            }
        except ObjectDoesNotExist:
            messages.info(self.request, "No active order")
            response = redirect('ecom_portal:home')
            response.delete_cookie('items')
            return response
        response = render(self.request, 'order-summary.html', context)
        response.delete_cookie('items')
        return response
# Previous Orders
class PastOrderView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        # Gets past order if it exists
        order = get_object_or_404(Order, user=self.request.user, ordered=True, id=kwargs['pk'])
        context = {
            'object': order,
            'past': True,
        }
        return render(self.request, 'order-summary.html', context)
# Payment page with link to stripe payment page
class PaymentView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        # Retrieves stripe account based on id
        stripe_id = UserProfile.objects.get(user=self.request.user).stripe_id
        res = stripe.Account.retrieve(stripe_id)
        if not res["charges_enabled"]:
            return redirect('ecom_portal:profile')
        # Gets order details and creates checkout session
        order = get_object_or_404(Order, user=self.request.user, ordered=False)
        context_order = {}
        for order_item in order.items.all():
            context_order[f"{order_item.item.vendor}"] = context_order.get(f"{order_item.item.vendor}", [order_item.item.vendor.location]) + [order_item]
        context = {'order': context_order, 'order_id': order.order_id}
        
        items = [{'name': item.item.title, 'amount': int(100*item.item.price), 'currency': 'usd', 'quantity': item.quantity} for item in order.items.all()]
        session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=items,
        success_url='https://domain.com/success',
        cancel_url='https://domain.com/failure',
        )
        context['session_id'] = session['id']
        order.payment_id = session['id']
        order.save()
        response = render(self.request, 'payment.html', context)
        response.delete_cookie('items')
        return response
    def post(self, *args, **kwargs):
        return redirect(str(self.request.POST))
# Webhook that Stripe will use after payment processed
webhook_secret = '' # Stripe webhook secret
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    try:
        event = stripe.Webhook.construct_event(
        payload, sig_header, webhook_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Gets information needed to render order summary page to send in email
        order = get_object_or_404(Order, payment_id = session['id'], ordered=False)
        transfer_g = str(uuid.uuid1())
        context_order = {}
        for order_item in order.items.all():
            context_order[f"{order_item.item.vendor}"] = context_order.get(f"{order_item.item.vendor}", [order_item.item.vendor.location]) + [order_item]
        context = {'order': context_order, 'order_id': order.order_id}
        subject = 'Order Received'
        html_message = render_to_string('order_confirmation_email.html', context)
        plain_message = strip_tags(html_message)
        from_email = 'email@gmail.com'
        to = order.user.email
        mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message)
        for vendor, items in order.get_vendor_transfers().items():
            amount = sum(item['price'] for item in items) * 100
            vendor_obj = VendorProfile.objects.get(approved=True,vendor_name=vendor)
            vendor_obj.payment_owed = float(vendor_obj.payment_owed) + sum(item['price'] for item in items)
            vendor_obj.save()
            order_confirm = OrderConfirmation.objects.create(user = order.user,
            vendor=VendorProfile.objects.get(approved=True, vendor_name=vendor),
            ordered_date = order.ordered_date,
            payment_id = order.payment_id,
            order_id = order.order_id,
            picked_up = False,)
            order_confirm.items.set(order.items.filter(item__vendor = VendorProfile.objects.get(approved = True, vendor_name=vendor)))
            order_confirm.save()
        order.ordered = True
        order.save()
        return HttpResponse(status=200)
# Shows after successful payment
class SuccessPaymentView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        context = {}
        return render(self.request, "success.html", context=context)
# Shows after failed payment
class FailurePaymentView(LoginRequiredMixin, TemplateView):
    def get(self, *args, **kwargs):
        context = {}
        return render(self.request, "failure.html", context=context)
# Adding an item to the cart
def add_to_cart(request, vendor, slug):
    # Gets item and creates cookie if no logged in
    item = get_object_or_404(Item, slug=slug, vendor__vendor_name=vendor)
    if request.user.is_anonymous:
        response = redirect(request.META["HTTP_REFERER"])
        if not request.COOKIES.get('items'):
            response.set_cookie('items', [{"name": item.slug, "vendor": item.vendor.vendor_name}])
        else:
            response.set_cookie('items', ast.literal_eval(request.COOKIES['items']) + [{"name": item.slug, "vendor": item.vendor.vendor_name}])
        messages.info(request, "This item was added to your cart")
        return response
    # Creates OrderItem and addsd it to order (order is created if no active order)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug, item__vendor__vendor_name=vendor).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item was updated.")
        else:
            messages.info(request, "This item was added to your cart.")
            order.items.add(order_item)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date
        )
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
    return redirect(request.META["HTTP_REFERER"])
# Remove all instances of an item from the cart
def remove_from_cart(request, vendor, slug):
    item = get_object_or_404(Item, slug=slug, vendor__vendor_name=vendor)
    if request.user.is_anonymous:
        response = redirect(request.META["HTTP_REFERER"])
        if not request.COOKIES.get('items'):
            messages.info(request, "You do not have any items in your cart")
        else:
            li = ast.literal_eval(request.COOKIES['items'])
            try:
                li.remove({"name": item.slug, "vendor": item.vendor.vendor_name})
            except ValueError:
                messages.info(request, "You do not have this item in your cart")
                return response
            response.set_cookie('items', li)
            messages.info(request, "This item was removed from your cart")
        return response
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug, item__vendor__vendor_name=vendor).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order_item.delete()
                order.delete()
            messages.info(request, "This item quantity was updated.")
        else:
            messages.info(request, "This item was not in your cart.")
    else:
        messages.info(request, "You do not have an active order.")
    return redirect(request.META["HTTP_REFERER"])
# Remove single instance of item from the cart
@login_required
def remove_item_from_cart(request, vendor, slug):
    item = get_object_or_404(Item, slug=slug,vendor__vendor_name=vendor)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug, item__vendor__vendor_name=vendor).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order_item.delete()
            messages.info(request, "This item was removed from cart.")
        else:
            messages.info(request, "This item was not in your cart.")
    else:
        messages.info(request, "You do not have an active order.")
    return redirect('ecom_portal:order-summary')
# Shows profile for user
class Profile(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        user_profile = UserProfile.objects.get(user=self.request.user)
        order_qs = Order.objects.filter(user=self.request.user, ordered=True)
        context = {
            'not_connected': True if stripe.Account.retrieve(user_profile.stripe_id)['charges_enabled'] else False,
            'object': order_qs,
            'is_vendor': VendorProfile.objects.filter(approved=True,user = self.request.user).exists(),
        }
        response = render(self.request, 'profile.html', context=context)
        response.delete_cookie('items')
        return response
    def post(self, *args, **kwargs):
        # Updates userprofile fields based on form
        user = UserProfile.objects.get(user=self.request.user)
        self.request.user.first_name = self.request.POST['first_name']
        self.request.user.last_name = self.request.POST['last_name']
        self.request.user.save()
        user.telephone = self.request.POST['telephone']
        user.street_address = self.request.POST['address']
        user.zip_code = self.request.POST['zip']
        user.save()
        return redirect(self.request.META["HTTP_REFERER"])
# Stripe page to set up connected account 
class StripeConnect(View):
    def get(self, *args, **kwargs):
        stripe_id = UserProfile.objects.get(user=self.request.user).stripe_id
        account_links = stripe.AccountLink.create(
        account=stripe_id,
        refresh_url='https://domain.com/accounts/profile',
        return_url='https://domain.com/accounts/profile',
        type='account_onboarding',
        )
        return redirect(account_links['url'])
def custom_transfer(request):
    if not request.user.is_superuser:
        return redirect(request.META["HTTP_REFERER"])
    amount = int(100*float(request.POST['amount'])*(1-fee))
    transfer = stripe.Transfer.create(
    amount=amount,
    currency='usd',
    destination=VendorProfile.objects.get(vendor_name=request.POST['vendor']).stripe_id)
    return redirect(request.META["HTTP_REFERER"])
# Upload inventory of items from excel sheet
def upload(request):
    if not request.user.groups.filter(name='Vendors').exists():
        return redirect(request.META["HTTP_REFERER"])
    uploaded_file = request.FILES['filename']
    wb = openpyxl.load_workbook(uploaded_file.file)
    sheet = wb['Inventory']
    for i in range(2, sheet.max_row+1):
        item, created = Item.objects.get_or_create(title=sheet[f'A{i}'].value, vendor=VendorProfile.objects.get(approved = True, user=request.user))
        item.price = sheet[f'B{i}'].value
        item.category = sheet[f'C{i}'].value
        item.description = sheet[f'D{i}'].value
        item.save()
        image = sheet._images[i-2]
        image = BytesIO(image._data())
        image = Image.open(image)
        image.save(MEDIA_ROOT + f'{item.vendor.vendor_name}_{item.slug}.png')
        item.image = f'{item.vendor.vendor_name}_{item.slug}.png'
        item.save()
    return redirect(request.META["HTTP_REFERER"])
def email_all(request):
    if request.user.is_superuser:
        user_emails = UserProfile.objects.all().values('email')
        return HttpResponse(",".join([u['email'] for u in user_emails if u['email']]))
# Evaluates cookies after user logs in
@receiver(user_logged_in, dispatch_uid="unique")
def user_logged_in_(request, user, **kwargs):
    try:
        print(ast.literal_eval(request.COOKIES['items']))
        order_qs = Order.objects.filter(user=request.user, ordered=False)
        if order_qs.exists():
            order = order_qs[0]
        else:
            ordered_date = timezone.now()
            order = Order.objects.create(
            user=request.user, ordered_date=ordered_date
            )
        for obj in ast.literal_eval(request.COOKIES['items']):
            item = get_object_or_404(Item, slug=obj['name'], vendor__vendor_name=obj['vendor'])
            order_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False
            )
            if order.items.filter(item__slug=item.slug, item__vendor__vendor_name=obj['vendor']).exists():
                order_item.quantity += 1
                order_item.save()
            else:
                order.items.add(order_item)

    except KeyError:
        print("No cookies with items")
