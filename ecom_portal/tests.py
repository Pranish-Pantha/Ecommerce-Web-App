from django.test import TestCase
from .models import Item
# Create your tests here.

class ItemTest(TestCase):
  def setUp(self):
    Item.objects.create(title="Item 1", price=11.4, category="C", slug="item1", description="description 1")
    Item.objects.create(title="Item 2", price=3.6, category="F", slug="item2", description="description 2")
    
  def access_items(self):
    item1 = Item.objects.get(title="Item 1")
    item2 = Item.objects.get(title="Item 2")
    self.assertEqual(item1.price, 11.4)
    self.assertEqual(item2.price, 3.6)
