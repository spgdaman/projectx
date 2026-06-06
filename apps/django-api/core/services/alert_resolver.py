from django.db.models import F, ExpressionWrapper, FloatField, Q
from core.models import Product, Deal, Category


def get_category_descendants(category):
    """
    Returns a set of all Category IDs that are descendants of (or equal to)
    the given category. Handles the self-referential parent FK tree.
    """
    ids = set()
    queue = [category]
    while queue:
        current = queue.pop()
        if current.id in ids:
            continue
        ids.add(current.id)
        queue.extend(list(current.children.all()))
    return ids


def product_scope(subscription):
    """Single product subscription."""
    if subscription.product_id is None:
        return []
    return [subscription.product]


def category_scope(subscription):
    """
    Products in the subscription's category AND all child categories, ordered
    by discount percentage (highest first).
    Paid users get top 5, free users get 2.
    """
    if subscription.category_id is None:
        return []
    limit = 5 if subscription.is_paid else 2

    cat_ids = get_category_descendants(subscription.category)

    return list(
        Product.objects.filter(
            master_category_id__in=cat_ids,
        ).filter(
            deal__isnull=False,
            deal__old_price__isnull=False,
            deal__current_price__lt=F('deal__old_price'),
        ).annotate(
            discount_pct=ExpressionWrapper(
                (F('deal__old_price') - F('deal__current_price'))
                / F('deal__old_price') * 100,
                output_field=FloatField(),
            )
        ).order_by('-discount_pct')
        .distinct()
        [:limit]
    )


def retailer_scope(subscription):
    """
    Products from the subscribed retailer with active deals, ordered by
    discount percentage (highest first). Includes branch-specific deals.
    Paid users get top 5, free users get 2.
    """
    if subscription.retailer_id is None:
        return []
    limit = 5 if subscription.is_paid else 2

    return list(
        Product.objects.filter(
            retailer=subscription.retailer,
        ).filter(
            deal__isnull=False,
            deal__old_price__isnull=False,
            deal__current_price__lt=F('deal__old_price'),
        ).annotate(
            discount_pct=ExpressionWrapper(
                (F('deal__old_price') - F('deal__current_price'))
                / F('deal__old_price') * 100,
                output_field=FloatField(),
            )
        ).order_by('-discount_pct')
        .distinct()
        [:limit]
    )


def resolve_alert_products(subscription):
    if subscription.target_type == 'product':
        return product_scope(subscription)
    if subscription.target_type == 'category':
        return category_scope(subscription)
    if subscription.target_type == 'retailer':
        return retailer_scope(subscription)
    return []
