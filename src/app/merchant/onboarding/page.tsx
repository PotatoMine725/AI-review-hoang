import { ContentDashboard } from "@/features/content-factory/dashboard";
export default function Page() { return <><ol className="flow-steps onboarding-steps"><li><span>01</span>Nhập thông tin sản phẩm</li><li><span>02</span>Theo dõi crawl / extract</li><li><span>03</span>Review và duyệt PKB</li></ol><ContentDashboard view="onboarding" merchant /></>; }
