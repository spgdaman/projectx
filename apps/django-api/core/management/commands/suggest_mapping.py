"""
Auto-suggest and create CategoryMapping entries using multi-signal string similarity.

Strategy (applied in order):
  1. Exact match (case-insensitive) → immediate map
  2. Token overlap ratio (Jaccard on word sets) — catches reordered words
  3. SequenceMatcher ratio — catches character-level similarity
  4. Partial ratio — checks if the shorter string is contained in the longer

Thresholds (tunable via CLI):
  --high   (default 0.80) → auto-map with high confidence
  --low    (default 0.50) → show as suggestion only (no auto-map)

Usage:
  python manage.py suggest_mapping
  python manage.py suggest_mapping --high 0.75 --low 0.45
  python manage.py suggest_mapping --dry-run   # preview without writing
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand

from core.models import Category, CategoryMapping, RetailerCategory

# Words that add noise when comparing categories
_STOP_WORDS = {
    "and", "or", "the", "a", "an", "of", "in", "for", "to", "with",
    "by", "&", "-", "/",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, split into words, drop stop words."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [w for w in text.split() if w and w not in _STOP_WORDS]


def _normalize(text: str) -> str:
    return " ".join(_tokenize(text))


def _jaccard(a_tokens: list[str], b_tokens: list[str]) -> float:
    """Token-overlap Jaccard similarity."""
    sa, sb = set(a_tokens), set(b_tokens)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _partial_ratio(shorter: str, longer: str) -> float:
    """Sliding window: best SequenceMatcher ratio of shorter vs any substring of longer."""
    if not shorter or not longer:
        return 0.0
    if len(shorter) > len(longer):
        shorter, longer = longer, shorter
    best = 0.0
    window = len(shorter)
    for i in range(len(longer) - window + 1):
        sub = longer[i: i + window]
        score = SequenceMatcher(None, shorter, sub).ratio()
        if score > best:
            best = score
    return best


def _combined_score(rcat_name: str, mcat_name: str) -> float:
    """
    Weighted combination of three signals.
    Returns a score in [0, 1].
    """
    r_norm = _normalize(rcat_name)
    m_norm = _normalize(mcat_name)

    # Exact after normalisation
    if r_norm == m_norm:
        return 1.0

    r_tok = _tokenize(rcat_name)
    m_tok = _tokenize(mcat_name)

    jaccard = _jaccard(r_tok, m_tok)
    seq = _seq_ratio(r_norm, m_norm)
    partial = _partial_ratio(r_norm, m_norm)

    # Weights: jaccard catches reordering well, seq/partial catch substring matches
    return 0.4 * jaccard + 0.35 * seq + 0.25 * partial


class Command(BaseCommand):
    help = "Suggest and auto-create CategoryMapping entries using multi-signal similarity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--high",
            type=float,
            default=0.80,
            help="Score threshold for auto-mapping (default: 0.80)",
        )
        parser.add_argument(
            "--low",
            type=float,
            default=0.50,
            help="Score threshold for showing suggestions without auto-mapping (default: 0.50)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview mappings without writing to the database",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=3,
            help="Number of top suggestions to show for low-confidence matches (default: 3)",
        )

    def handle(self, *args, **options):
        high_threshold: float = options["high"]
        low_threshold: float = options["low"]
        dry_run: bool = options["dry_run"]
        top_n: int = options["top"]

        unmapped = list(
            RetailerCategory.objects.filter(mapping__isnull=True)
            .select_related("retailer")
            .order_by("retailer__name", "name")
        )
        masters = list(Category.objects.all().order_by("name"))

        if not unmapped:
            self.stdout.write(self.style.SUCCESS("All retailer categories are already mapped!"))
            return

        if not masters:
            self.stdout.write(self.style.ERROR("No master categories exist yet. Create some first."))
            return

        self.stdout.write(
            f"Unmapped: {len(unmapped)}  |  Master categories: {len(masters)}  |  "
            f"High threshold: {high_threshold}  |  Low threshold: {low_threshold}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — no mappings will be saved."))
        self.stdout.write("-" * 70)

        auto_mapped = 0
        suggestions = []
        no_match = []

        for rcat in unmapped:
            # Score against every master category
            scored = [
                (mcat, _combined_score(rcat.name, mcat.name))
                for mcat in masters
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            best_mcat, best_score = scored[0]

            if best_score >= high_threshold:
                if not dry_run:
                    CategoryMapping.objects.get_or_create(
                        retailer_category=rcat,
                        defaults={"master_category": best_mcat},
                    )
                auto_mapped += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[AUTO] {rcat.retailer.name} › {rcat.name!r:<35} "
                        f"→  {best_mcat.name!r}  ({best_score:.2f})"
                    )
                )
            elif best_score >= low_threshold:
                top_matches = [
                    f"{mc.name!r} ({sc:.2f})"
                    for mc, sc in scored[:top_n]
                ]
                suggestions.append((rcat, top_matches))
                self.stdout.write(
                    self.style.WARNING(
                        f"[SUGGEST] {rcat.retailer.name} › {rcat.name!r:<30} "
                        f"→  {' | '.join(top_matches)}"
                    )
                )
            else:
                no_match.append(rcat)
                self.stdout.write(
                    f"[NO MATCH] {rcat.retailer.name} › {rcat.name!r}  "
                    f"(best: {best_mcat.name!r} {best_score:.2f})"
                )

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(f"Auto-mapped  : {auto_mapped}")
        self.stdout.write(f"Suggestions  : {len(suggestions)}  (review in admin)")
        self.stdout.write(f"No match     : {len(no_match)}")

        if no_match:
            self.stdout.write(
                "\nCategories with no close match — consider adding them as master categories:"
            )
            for r in no_match:
                self.stdout.write(f"  • {r.retailer.name}: {r.name}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY-RUN — no changes were written."))
