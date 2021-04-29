from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.shortcuts import reverse
import PIL
import requests
import json
import stripe
import string
import random
import ast
from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent
stripe.api_key = "" # Stripe key
CATEGORY_CHOICES = (
    ('C', 'Clothing'),
    ('G', 'Groceries'),
    ('E', 'Electronics')
)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    telephone = models.CharField(max_length=10, null=True, blank=True)
    street_address = models.CharField(max_length=100, null=True, blank=True)
    apartment_address = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=100, null=True, blank=True)
    stripe_id = models.CharField(max_length=100, null=True)
    def __str__(self):
        return self.user.username
    def save(self, *args, **kwargs):
        self.first_name = self.user.first_name
        self.last_name = self.user.last_name
        self.email = self.user.email
        super().save(*args, **kwargs)
class VendorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vendor_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100, null=True)
    zip_code = models.IntegerField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    logo = models.ImageField(null=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=1, null=True)
    stripe_id = models.CharField(max_length=100, null=True)
    approved = models.BooleanField(default=False)
    payment_owed = models.FloatField(default=0.0)
    def __str__(self):
        return self.vendor_name
    def get_zip(self):
        return self.zip_code
    def save(self, *args, **kwargs):
        query = self.location.replace(" ", "+")
        res = requests.get(f'https://geocode.search.hereapi.com/v1/geocode?q={query}&apiKey=') # Add in HERE API Key
        res = json.loads(res.content)
        self.latitude = res['items'][0]['position']['lat']
        self.longitude = res['items'][0]['position']['lng']
        user_profile = UserProfile.objects.get(user=self.user)
        self.stripe_id = user_profile.stripe_id
        super().save(*args, **kwargs)
class Item(models.Model):
    title = models.CharField(max_length=100)
    price = models.FloatField(null=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=1)
    slug = models.SlugField()
    description = models.TextField()
    image = models.ImageField(default='default.png')
    vendor = models.ForeignKey('VendorProfile', on_delete=models.CASCADE, null=True, blank=True)
    class Meta:
        unique_together = ('slug', 'vendor',)
    def get_absolute_url(self):
        return reverse('ecom_portal:product', kwargs={
            'slug': self.slug,
            'vendor': self.vendor.vendor_name
        })
    def get_add_to_cart_url(self):
        return reverse('ecom_portal:add-to-cart', kwargs={
            'slug': self.slug,
            'vendor': self.vendor.vendor_name
        })
    def get_remove_from_cart_url(self):
        return reverse('ecom_portal:remove-from-cart', kwargs={
            'slug': self.slug,
            'vendor': self.vendor.vendor_name
        })
    def __str__(self):
        return self.title
    def save(self, *args, **kwargs):
        self.slug = self.title.lower().replace(' ', '-')
        super().save(*args, **kwargs)
class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    def get_total_item_price(self):
        return self.quantity * self.item.price
    def __str__(self):
        return f"{self.user}|{self.quantity}|{self.item.title}#{self.id}"
class Order(models.Model):
    order_id = models.CharField(max_length = 100, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    payment_id = models.CharField(max_length = 100, null=True)
    ordered = models.BooleanField(default=False)
    picked_up = models.BooleanField(default=False)
    def save(self, *args, **kwargs):
        if not self.pk:
            self.order_id = ''.join(random.choices(string.ascii_uppercase, k=4))
            super(Order, self).save(*args, **kwargs)
            self.order_id += str(self.pk)
            self.save()
        else:
            super(Order, self).save(*args, **kwargs)
    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_total_item_price()
        return total
    def get_vendor_transfers(self):
        vendors = {}
        for order_item in self.items.all():
            if order_item.item.vendor.vendor_name not in vendors.keys():
                vendors[order_item.item.vendor.vendor_name] = [{'title': order_item.item.title, 'price': order_item.get_total_item_price(), 'quantity': order_item.quantity}]
            else:
                vendors[order_item.item.vendor.vendor_name].append({'title': order_item.item.title, 'price': order_item.get_total_item_price(), 'quantity': order_item.quantity})
        return vendors
    def __str__(self):
        return f"Order for {self.user.username}"
class OrderConfirmation(models.Model):
    order_id = models.CharField(max_length=100, null=True)
    vendor = models.ForeignKey('VendorProfile', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    items = models.ManyToManyField(OrderItem)
    ordered_date = models.DateTimeField()
    payment_id = models.CharField(max_length = 100, null=True)
    picked_up = models.BooleanField(default=False)
    def __str__(self):
        return f"Order Confirmation for {self.user.username}"
def userprofile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        userprofile = UserProfile.objects.create(user=instance)
        res = stripe.Account.create(
        type="express",
        country="US",
        email=userprofile.email,
        business_type = 'individual',
        )
        res_id = res['id']
        userprofile.stripe_id = res_id
        userprofile.save()
def order_deletion(sender, instance, *args, **kwargs):
    print(instance.items.all())
    print(type(instance.items))
    instance.items.all().delete()
@receiver(post_delete, sender=Item)
def submission_delete(sender, instance, **kwargs):
    if instance.image.name != 'default.png':
        instance.image.delete(False)
post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)
pre_delete.connect(order_deletion, sender=Order)
