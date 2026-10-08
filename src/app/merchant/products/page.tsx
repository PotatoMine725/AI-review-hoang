import Link from "next/link";
import { ContentDashboard } from "@/features/content-factory/dashboard";
export default function Page() { return <><Link className="portal-primary product-add-link" href="/merchant/onboarding">Thêm sản phẩm</Link><ContentDashboard view="products" merchant /></>; }
