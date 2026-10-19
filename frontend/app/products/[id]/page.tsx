import Link from "next/link";
import { notFound } from "next/navigation";

import { getProduct } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const productId = Number(id);
  if (!Number.isInteger(productId) || productId <= 0) {
    notFound();
  }

  const product = await getProduct(productId);
  if (product === null) {
    notFound();
  }

  return (
    <main>
      <p>
        <Link href="/">← Каталог</Link>
      </p>
      <h1>{product.title}</h1>
      <img src={product.image_url} alt={product.title} width={400} />
    </main>
  );
}
