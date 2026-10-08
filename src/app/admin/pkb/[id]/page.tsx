import { ProductDetail } from "@/features/content-factory/product-detail";
export default async function Page({ params }: PageProps<"/admin/pkb/[id]">) { const { id } = await params; return <ProductDetail id={id} actor="admin" />; }
