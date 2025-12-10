from django.core.management.base import BaseCommand
from core.models import Category


CATEGORIES = {
    "Fresh Food": [
        "Fruits",
        "Vegetables",
        "Herbs & Seasonings",
        "Fresh Juice & Cut Fruit",
        "Fresh Salads",
        "Fresh Bakery Bread"
    ],
    "Food Cupboard": [
        "Rice",
        "Pasta & Noodles",
        "Flour & Baking Supplies",
        "Sugar & Salt",
        "Cooking Oil",
        "Canned Food & Tinned Goods",
        "Cereals",
        "Spices & Condiments",
        "Snacks & Confectionery",
        "Tea, Coffee & Beverages",
        "Sauces & Spreads"
    ],
    "Dairy & Chilled": [
        "Milk",
        "Yoghurt",
        "Cheese",
        "Butter & Margarine",
        "Eggs",
        "Chilled Juices"
    ],
    "Frozen Foods": [
        "Frozen Chips",
        "Frozen Vegetables",
        "Ice Cream",
        "Frozen Meat & Chicken",
        "Frozen Snacks"
    ],
    "Meat & Poultry": [
        "Beef",
        "Poultry",
        "Goat & Mutton",
        "Mince & Sausages",
        "Processed Meat"
    ],
    "Fish & Seafood": [
        "Fresh Fish",
        "Smoked Fish",
        "Frozen Fish",
        "Seafood"
    ],
    "Bakery": [
        "Bread",
        "Cakes & Pastries",
        "Doughnuts",
        "Buns & Rolls"
    ],
    "Drinks": [
        "Soft Drinks",
        "Water",
        "Energy Drinks",
        "Juices",
        "Hot Beverage Powders"
    ],
    "Household & Cleaning": [
        "Laundry Supplies",
        "Dishwashing",
        "Surface Cleaners",
        "Air Fresheners",
        "Toilet Tissue & Paper Products",
        "Insecticides",
        "Household Organisation",
        "Light Bulbs & Batteries"
    ],
    "Baby Products": [
        "Diapers",
        "Wipes",
        "Baby Food",
        "Baby Bath & Skincare",
        "Baby Feeding Items",
        "Baby Health"
    ],
    "Beauty & Personal Care": [
        "Hair Care",
        "Skin Care",
        "Bath & Body",
        "Fragrances",
        "Oral Care",
        "Men’s Grooming",
        "Shaving & Razors",
        "Beauty Tools"
    ],
    "Health & Pharmacy": [
        "Vitamins & Supplements",
        "Over-the-Counter Medicine",
        "First Aid",
        "Sexual Health",
        "Medical Devices"
    ],
    "Home & Kitchen": [
        "Cookware",
        "Utensils",
        "Small Appliances",
        "Tableware",
        "Storage Containers",
        "Bedding & Linens"
    ],
    "Electronics": [
        "TVs",
        "Audio Equipment",
        "Phones",
        "Tablets & Laptops",
        "Accessories",
        "Smart Devices"
    ],
    "Stationery & Office": [
        "School Supplies",
        "Notebooks & Pens",
        "Printing Paper",
        "Desk Accessories"
    ],
    "Pet Supplies": [
        "Dog Food",
        "Cat Food",
        "Pet Accessories"
    ],
    "Liquor": [
        "Beer",
        "Wine",
        "Spirits",
        "Ciders"
    ],
    "Automotive": [
        "Car Care",
        "Car Accessories"
    ],
    "Gardening & Outdoors": [
        "Seeds",
        "Tools",
        "Outdoor Accessories"
    ]
}

class Command(BaseCommand):
    help = "Populate the master Category table with hierarchical categories."

    def handle(self, *args, **kwargs):
        self.stdout.write("Populating categories...")

        for parent_name, children in CATEGORIES.items():
            parent_cat, created = Category.objects.get_or_create(
                name=parent_name,
                parent=None
            )
            if created:
                self.stdout.write(f"Created parent category: {parent_name}")
            else:
                self.stdout.write(f"Parent already exists: {parent_name}")

            for child_name in children:
                child_cat, c_created = Category.objects.get_or_create(
                    name=child_name,
                    parent=parent_cat
                )
                if c_created:
                    self.stdout.write(f"  Created child category: {parent_name} > {child_name}")
                else:
                    self.stdout.write(f"  Child already exists: {parent_name} > {child_name}")

        self.stdout.write(self.style.SUCCESS("Category population complete!"))
