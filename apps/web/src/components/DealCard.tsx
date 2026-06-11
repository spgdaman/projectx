"use client";

import posthog from "posthog-js";

const CATEGORY_ICONS: Record<string, { icon: string; bg: string }> = {
  "electronics": { icon: "📱", bg: "bg-blue-50" },
  "appliances": { icon: "🏠", bg: "bg-blue-50" },
  "phones": { icon: "📱", bg: "bg-blue-50" },
  "tv": { icon: "📺", bg: "bg-blue-50" },
  "food": { icon: "🛒", bg: "bg-green-50" },
  "beverages": { icon: "🥤", bg: "bg-green-50" },
  "fresh": { icon: "🥬", bg: "bg-green-50" },
  "dairy": { icon: "🥛", bg: "bg-green-50" },
  "meat": { icon: "🥩", bg: "bg-green-50" },
  "bakery": { icon: "🍞", bg: "bg-green-50" },
  "snacks": { icon: "🍿", bg: "bg-green-50" },
  "confectionery": { icon: "🍫", bg: "bg-green-50" },
  "breakfast": { icon: "🥣", bg: "bg-green-50" },
  "cooking": { icon: "🫙", bg: "bg-green-50" },
  "frozen": { icon: "🧊", bg: "bg-green-50" },
  "condiments": { icon: "🫙", bg: "bg-green-50" },
  "pasta": { icon: "🍝", bg: "bg-green-50" },
  "personal care": { icon: "🧴", bg: "bg-pink-50" },
  "beauty": { icon: "💄", bg: "bg-pink-50" },
  "body": { icon: "🧴", bg: "bg-pink-50" },
  "hair": { icon: "💇", bg: "bg-pink-50" },
  "oral": { icon: "🪥", bg: "bg-pink-50" },
  "sanitary": { icon: "🧴", bg: "bg-pink-50" },
  "health": { icon: "💊", bg: "bg-pink-50" },
  "home care": { icon: "🧹", bg: "bg-yellow-50" },
  "household": { icon: "🏠", bg: "bg-yellow-50" },
  "kitchen": { icon: "🍳", bg: "bg-orange-50" },
  "laundry": { icon: "🫧", bg: "bg-yellow-50" },
  "cleaning": { icon: "🧹", bg: "bg-yellow-50" },
  "tissue": { icon: "🧻", bg: "bg-yellow-50" },
  "liquor": { icon: "🍷", bg: "bg-red-50" },
  "spirits": { icon: "🥃", bg: "bg-red-50" },
  "beer": { icon: "🍺", bg: "bg-red-50" },
  "wines": { icon: "🍷", bg: "bg-red-50" },
  "wine": { icon: "🍷", bg: "bg-red-50" },
  "fashion": { icon: "👗", bg: "bg-purple-50" },
  "textile": { icon: "👕", bg: "bg-purple-50" },
  "luggage": { icon: "🧳", bg: "bg-purple-50" },
  "pet": { icon: "🐾", bg: "bg-amber-50" },
};

function getCategoryStyle(categoryName?: string | null): { icon: string; bg: string } {
  if (!categoryName) return { icon: "🏷️", bg: "bg-gray-50" };
  const lower = categoryName.toLowerCase();
  for (const [key, val] of Object.entries(CATEGORY_ICONS)) {
    if (lower.includes(key)) return val;
  }
  return { icon: "🏷️", bg: "bg-brand-50" };
}

interface Deal {
  id: number;
  product: {
    id?: number;
    name: string;
    image_url?: string | null;
    master_category?: { id?: number; name: string } | null;
  };
  retailer: { id?: number; name: string };
  current_price: number | string;
  old_price?: number | string | null;
  discount_pct?: number | null;
  link?: string | null;
}

interface Props {
  deal: Deal;
  onSubscribe?: (deal: Deal) => void;
}

export function DealCard({ deal, onSubscribe }: Props) {
  const currentPrice = Number(deal.current_price);
  const oldPrice = deal.old_price != null ? Number(deal.old_price) : null;
  const { icon, bg } = getCategoryStyle(deal.product.master_category?.name);
  const hasImage = !!deal.product.image_url;

  return (
    <div className="bg-white rounded-xl border border-gray-100 hover:shadow-md transition-shadow flex flex-col overflow-hidden group">
      {/* Product image / placeholder */}
      <div className={`relative w-full h-36 overflow-hidden ${bg}`}>
        {hasImage && (
          <img
            src={deal.product.image_url!}
            alt={deal.product.name}
            className="absolute inset-0 w-full h-full object-contain p-2"
            onError={(e) => {
              const img = e.currentTarget;
              img.style.display = "none";
              const ph = img.nextElementSibling as HTMLElement | null;
              if (ph) ph.style.display = "flex";
            }}
          />
        )}
        {/* Placeholder — always flex-centered; hidden behind image when image loads */}
        <div
          className="absolute inset-0 items-center justify-center"
          style={{ display: hasImage ? "none" : "flex" }}
        >
          <span className="text-5xl opacity-60">{icon}</span>
        </div>

        {/* Discount badge overlay */}
        {deal.discount_pct != null && deal.discount_pct > 0 && (
          <div className="absolute top-2 right-2 bg-red-500 text-white text-xs font-extrabold px-2 py-0.5 rounded-full shadow">
            -{Math.round(deal.discount_pct)}%
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex flex-col flex-1 p-3 gap-1.5">
        {/* Retailer badge */}
        <span className="self-start inline-block bg-brand-50 text-brand-700 text-xs font-bold px-2 py-0.5 rounded-full">
          {deal.retailer.name}
        </span>

        {/* Product name */}
        <p className="text-sm font-semibold text-gray-900 line-clamp-2 leading-snug flex-1">
          {deal.product.name}
        </p>

        {deal.product.master_category && (
          <p className="text-xs text-gray-400">{deal.product.master_category.name}</p>
        )}

        {/* Price */}
        <div className="flex items-baseline gap-2 pt-1 border-t border-gray-50 mt-auto">
          <span className="text-base font-extrabold text-brand-600">
            KES {currentPrice.toLocaleString()}
          </span>
          {oldPrice != null && oldPrice > currentPrice && (
            <span className="text-xs text-gray-400 line-through">
              {oldPrice.toLocaleString()}
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          {onSubscribe && (
            <button
              onClick={() => onSubscribe(deal)}
              className="flex-1 text-xs font-semibold bg-brand-600 hover:bg-brand-700 text-white rounded-lg py-1.5 transition"
            >
              🔔 Alert
            </button>
          )}
          {deal.link && (
            <a
              href={deal.link}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() =>
                posthog.capture("deal_link_clicked", {
                  deal_id: deal.id,
                  product_id: deal.product.id,
                  product_name: deal.product.name,
                  retailer: deal.retailer.name,
                  current_price: deal.current_price,
                  discount_pct: deal.discount_pct,
                })
              }
              className="flex-1 text-xs font-semibold border border-gray-200 text-gray-600 hover:border-brand-400 hover:text-brand-600 rounded-lg py-1.5 text-center transition"
            >
              View ↗
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
