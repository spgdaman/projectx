from django import forms
from core.models import Subscription, Product, Category, Retailer

class PhoneLoginForm(forms.Form):
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "Phone number"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )
    
class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['target_type', 'product', 'category', 'retailer',]

def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # Always load categories and retailers
    self.fields['category'].queryset = Category.objects.all()
    self.fields['retailer'].queryset = Retailer.objects.all()

    # Default: hide product queryset
    self.fields['product'].queryset = Product.objects.none()

    # If form submitted
    if 'target_type' in self.data:
        target_type = self.data.get('target_type')
        if target_type == 'product':
            self.fields['product'].queryset = Product.objects.all()
        elif target_type == 'category':
            self.fields['category'].queryset = Category.objects.all()
        elif target_type == 'retailer':
            self.fields['retailer'].queryset = Retailer.objects.all()

    # If editing an existing subscription
    elif self.instance.pk:
        if self.instance.target_type == 'product' and self.instance.product:
            # Populate all products so dropdown works
            self.fields['product'].queryset = Product.objects.all()
        elif self.instance.target_type == 'category' and self.instance.category:
            self.fields['category'].queryset = Category.objects.all()
        elif self.instance.target_type == 'retailer' and self.instance.retailer:
            self.fields['retailer'].queryset = Retailer.objects.all()
