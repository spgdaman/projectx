from core.models import Product

def product_scope(subscription):
    return [subscription.product]

def category_scope(subscription):
    limit = 3 if subscription.is_paid else 1
    return list(
        Product.objects.filter(master_category=subscription.category)
        .order_by("-price")[:limit]
    )

def retailer_scope(subscription):
    limit = 3 if subscription.is_paid else 1
    return list(
        Product.objects.filter(retailer=subscription.retailer)
        .order_by("-price")[:limit]
    )

def resolve_alert_products(subscription):
    if subscription.target_type == "product":
        return product_scope(subscription)

    if subscription.target_type == "category":
        return category_scope(subscription)

    if subscription.target_type == "retailer":
        return retailer_scope(subscription)

    return []
