from django.core.management.base import BaseCommand
from difflib import SequenceMatcher
from core.models import RetailerCategory, Category, CategoryMapping

class Command(BaseCommand):
    help = "Suggest master category mappings and optionally save them"

    def handle(self, *args, **options):
        unmapped = RetailerCategory.objects.filter(mapping__isnull=True).order_by("retailer__name")
        masters = list(Category.objects.all())

        if not unmapped:
            self.stdout.write(self.style.SUCCESS("All retailer categories are already mapped!"))
            return

        for rcat in unmapped:
            best_match = None
            best_score = 0

            for mcat in masters:
                score = SequenceMatcher(None, rcat.name.lower(), mcat.name.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = mcat

            if best_match and best_score >= 0.55:
                # Auto-create mapping
                mapping, created = CategoryMapping.objects.get_or_create(
                    retailer_category=rcat,
                    defaults={'master_category': best_match}
                )

                if created:
                    self.stdout.write(
                        f"[AUTO-MAPPED] {rcat.retailer.name} → {rcat.name}  --->  {best_match.name} ({best_score:.2f})"
                    )
                else:
                    self.stdout.write(
                        f"[EXISTS] {rcat.retailer.name} → {rcat.name} already mapped"
                    )
            else:
                self.stdout.write(
                    f"[NO MATCH] {rcat.retailer.name} → {rcat.name}"
                )
