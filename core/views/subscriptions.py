from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Subscription, Product, Category, Retailer
from core.forms import SubscriptionForm

@login_required
def subscription_list(request):
    subs = Subscription.objects.filter(user=request.user)
    if request.user.is_authenticated:
        messages.success(request, "Payment successful! Your subscription is now active.")
    return render(request, "core/subscription_list.html", {"subscriptions": subs})

@login_required
def subscription_create(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.user = request.user
            sub.save()
            return redirect("subscription_list")
    else:
        form = SubscriptionForm()
    return render(request, "core/subscription_form.html", {"form": form, "action": "Create"})

@login_required
def subscription_update(request, pk):
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == "POST":
        form = SubscriptionForm(request.POST, instance=sub)
        if form.is_valid():
            form.save()
            return redirect("subscription_list")
    else:
        form = SubscriptionForm(instance=sub)
    return render(request, "core/subscription_form.html", {"form": form, "action": "Update"})

@login_required
def subscription_deactivate(request, pk):
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    sub.is_active = False
    sub.save()
    return redirect("subscription_list")
