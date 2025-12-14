from django import forms
from core.models import Subscription, Product, Category, Retailer

class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ["target_type", "product", "category", "retailer", "is_paid"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initially hide all fields
        self.fields["product"].queryset = Product.objects.none()
        self.fields["category"].queryset = Category.objects.all()
        self.fields["retailer"].queryset = Retailer.objects.all()

        if self.instance and self.instance.pk:
            # Show only the relevant field for update
            if self.instance.target_type == "product":
                self.fields["product"].queryset = Product.objects.all()
            elif self.instance.target_type == "category":
                self.fields["category"].queryset = Category.objects.all()
            elif self.instance.target_type == "retailer":
                self.fields["retailer"].queryset = Retailer.objects.all()
