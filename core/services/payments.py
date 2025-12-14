def activate_subscription(subscription):
    subscription.is_paid = True
    subscription.is_free_tier = False
    subscription.is_active = True
    subscription.save()
