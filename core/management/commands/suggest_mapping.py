# core/management/commands/suggest_mapping.py
from django.core.management.base import BaseCommand
from difflib import SequenceMatcher
from core.models import RetailerCategory, Category, CategoryMapping

def normalize(text):
    """
    Normalize strings for better matching.
    """
    return text.lower().replace("-", " ").strip()

class Command(BaseCommand):
    help = "Suggest and optionally auto-map RetailerCategory → Master Category"

    THRESHOLD = 0.45  # similarity threshold for auto-mapping

    def handle(self, *args, **options):
        unmapped = RetailerCategory.objects.filter(mapping__isnull=True).order_by("retailer__name")
        masters = list(Category.objects.all())

        if not unmapped:
            self.stdout.write(self.style.SUCCESS("All retailer categories are already mapped!"))
            return

        self.stdout.write(f"Found {unmapped.count()} unmapped retailer categories.\n")
        auto_mapped = 0
        no_match = []

        for rcat in unmapped:
            best_match = None
            best_score = 0

            for mcat in masters:
                score = SequenceMatcher(None, normalize(rcat.name), normalize(mcat.name)).ratio()
                if score > best_score:
                    best_score = score
                    best_match = mcat

            if best_match and best_score >= self.THRESHOLD:
                # Auto-create mapping
                mapping, created = CategoryMapping.objects.get_or_create(
                    retailer_category=rcat,
                    defaults={'master_category': best_match}
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[AUTO-MAPPED] {rcat.retailer.name} → {rcat.name}  →  {best_match.name} ({best_score:.2f})"
                        )
                    )
                    auto_mapped += 1
                else:
                    self.stdout.write(
                        f"[EXISTS] {rcat.retailer.name} → {rcat.name} already mapped"
                    )
            else:
                no_match.append(rcat)
                self.stdout.write(
                    self.style.WARNING(
                        f"[NO MATCH] {rcat.retailer.name} → {rcat.name} (best score: {best_score:.2f})"
                    )
                )

        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"Auto-mapped: {auto_mapped}")
        self.stdout.write(f"Unmapped remaining: {len(no_match)}")
        if no_match:
            self.stdout.write("You can manually map these categories in the admin or add them to master categories:")
            for r in no_match:
                self.stdout.write(f"- {r.retailer.name}: {r.name}")
