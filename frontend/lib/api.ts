export type Product = {
  id: number;
  title: string;
  image_url: string;
  created_at: string;
};

// Server-side only: the pages are rendered on the server and talk to the API inside the cluster network.
const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

// cache: "no-store": every request reads fresh data from the API. Nothing is cached in the process or on
// disk, so all replicas show the same catalog right after a product is added.
export async function getProducts(): Promise<Product[]> {
  const response = await fetch(`${API_URL}/api/products`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Catalog API answered ${response.status}`);
  }
  return response.json();
}

export async function getProduct(id: number): Promise<Product | null> {
  const response = await fetch(`${API_URL}/api/products/${id}`, { cache: "no-store" });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Catalog API answered ${response.status}`);
  }
  return response.json();
}
