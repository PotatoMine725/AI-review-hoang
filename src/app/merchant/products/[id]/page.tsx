import { ProductDetail } from "@/features/content-factory/product-detail";
export default async function Page({ params }: PageProps<"/merchant/products/[id]">) { const { id } = await params; return <ProductDetail id={id} actor="merchant" />; }
