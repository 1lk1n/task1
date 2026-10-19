import Link from "next/link";

import { getProducts } from "@/lib/api";

// Rendered on every request (no static page, no ISR cache on disk).
export const dynamic = "force-dynamic";

export default async function CatalogPage() {
  const products = await getProducts();

  return (
    <main>
      <h1>Каталог</h1>
      {products.length === 0 ? (
        <p>Товаров пока нет.</p>
      ) : (
        <ul>
          {products.map((product) => (
            <li key={product.id}>
              <Link href={`/products/${product.id}`}>
                <img src={product.image_url} alt={product.title} width={160} />
                <div>{product.title}</div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
