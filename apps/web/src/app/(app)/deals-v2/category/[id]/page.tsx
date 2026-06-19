import { CategoryPageClient } from "./_content";

// Server Component — awaits params (required in Next.js 15)
export default async function CategoryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CategoryPageClient categoryId={Number(id)} />;
}
