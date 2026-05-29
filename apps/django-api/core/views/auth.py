from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from core.forms import PhoneLoginForm


def login_view(request):
    if request.method == "POST":
        form = PhoneLoginForm(request.POST)

        if form.is_valid():
            phone = form.cleaned_data["phone_number"]
            password = form.cleaned_data["password"]

            user = authenticate(
                request,
                phone_number=phone,
                password=password
            )

            if user:
                login(request, user)
                return redirect("subscription_list")  # change to your home page
            else:
                messages.error(request, "Invalid phone number or password")

    else:
        form = PhoneLoginForm()

    return render(request, "auth/login.html", {"form": form})
