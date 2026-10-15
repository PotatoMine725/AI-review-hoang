"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, ArrowUpRight, Check, CheckCheck, FileCheck2, Film, Link2, Mic2, SlidersHorizontal, Sparkles } from "lucide-react";
import { usePreferences } from "@/features/studio/preferences";
import { initialStudio } from "@/features/studio/model";
import { PublicLayout } from "./public-layout";

function StudioPreview() {
  const { t } = usePreferences();
  const [ratio, setRatio] = useState("9:16");
  const [preset, setPreset] = useState(0);
  const presets = [t("Hoạt hình đồ họa", "Motion graphics"), t("Điện ảnh tối giản", "Minimal cinema"), t("Cổ điển", "Vintage")];
  return <figure className="landing-preview" aria-label={t("Minh họa tùy chọn video", "Video options illustration")}>
    <div className="preview-topline"><span><Sparkles size={13} aria-hidden="true" /> REVIEWLAB STUDIO</span><span>{t("Minh họa", "Illustration")}</span></div>
    <div className="preview-stage" data-preset={preset}>
      <div className="preview-orbit" aria-hidden="true" />
      <div className={`preview-film ${ratio === "16:9" ? "is-landscape" : ""}`}>
        <div className="preview-film-header"><span>DAILY OBJECTS / 01</span><span>{ratio}</span></div>
        <div className="preview-product" aria-hidden="true"><div className="preview-plinth" /><div className="preview-bottle"><span>daily.</span></div><div className="preview-bottle second"><span>daily.</span></div></div>
        <div className="preview-caption"><small>{t("MỘT CHÚT CẢM HỨNG MỖI NGÀY", "A LITTLE EVERYDAY INSPIRATION")}</small><strong>{t("Mang theo", "Take a little")}<br />{t("điều bạn thích.", "of what you love.")}</strong></div>
        <div className="preview-subtitle">{t("Một người bạn cho mọi hành trình.", "A companion for every journey.")}</div>
        <div className="preview-film-footer"><span>REVIEWLAB</span><span>00:18</span></div>
      </div>
      <div className="preview-floating"><CheckCheck size={16} aria-hidden="true" /><div><strong>{t("Câu chuyện của bạn", "Your own story")}</strong><span>{t("Từ thông tin sản phẩm", "From product information")}</span></div></div>
    </div>
    <div className="preview-controls">
      <div className="preview-ratio"><span>{t("Khung hình", "Format")}</span><div role="group" aria-label={t("Chọn khung hình minh họa", "Illustration format")}>{["9:16", "16:9"].map(value => <button key={value} type="button" aria-pressed={ratio === value} onClick={() => setRatio(value)}>{value}</button>)}</div></div>
      <div className="preview-presets" role="group" aria-label={t("Chọn phong cách minh họa", "Illustration style")}>{presets.map((name, index) => <button type="button" key={name} aria-pressed={preset === index} onClick={() => setPreset(index)}>{name}</button>)}</div>
    </div>
    <figcaption>{t("Thử đổi khung hình và phong cách. Đây là hình minh họa, không phải video đã tạo.", "Try a format and style. This is an illustration, not a generated video.")}</figcaption>
  </figure>;
}

export function LandingPage() {
  const { t, number } = usePreferences();
  const steps = [
    { icon: Link2, title: t("Bắt đầu bằng một link", "Start with a link"), text: t("Dán link website hoặc trang bán sản phẩm bạn muốn giới thiệu.", "Paste a website or product page you want to introduce.") },
    { icon: FileCheck2, title: t("Kiểm tra thông tin", "Check the details"), text: t("Xem nguồn, chỉnh sửa nội dung và xác nhận thông tin trước khi sáng tạo.", "Review sources, edit the content and confirm product details before creating.") },
    { icon: Film, title: t("Tạo câu chuyện bằng video", "Tell your story in video"), text: t("Chọn phong cách, khung hình rồi tạo, xem và tải video trong dự án.", "Choose a style and format, then create, watch and download videos in your project.") },
  ];
  return <PublicLayout landing>
    <main id="main-content" tabIndex={-1}>
      <section className="landing-hero public-container" aria-labelledby="hero-title">
        <div className="hero-copy">
          <span className="landing-eyebrow"><span className="landing-dot" />{t("KHÔNG GIAN SÁNG TẠO VIDEO", "YOUR VIDEO WORKSPACE")}</span>
          <h1 id="hero-title">{t("Một đường link.", "One product link.")}<br /><span>{t("Nhiều cách", "More ways")} <br />{t("kể chuyện.", "to tell its story.")}</span></h1>
          <p>{t("Biến thông tin sản phẩm thành ý tưởng video review. Kiểm tra nội dung, chọn phong cách và kể câu chuyện theo cách của bạn với Reviewlab.", "Turn product information into ideas for review videos. Check the content, choose a style and tell the story your way with Reviewlab.")}</p>
          <div className="hero-actions"><Link className="primary-button" href="/signup">{t("Bắt đầu sáng tạo", "Start creating")}<ArrowUpRight size={17} aria-hidden="true" /></Link><a className="hero-process-link" href="#quy-trinh">{t("Khám phá quy trình", "See how it works")}<ArrowRight size={16} aria-hidden="true" /></a></div>
          <p className="hero-preview-note"><span>{t("BẢN XEM THỬ", "PREVIEW")}</span>{t("Khám phá giao diện với dữ liệu mẫu.", "Explore the interface with sample data.")}</p>
        </div>
        <StudioPreview />
      </section>
      <div className="landing-capabilities public-container" aria-label={t("Khả năng được giới thiệu", "Capabilities overview")}>
        <span><Link2 size={16} aria-hidden="true" />{t("Từ link sản phẩm", "From a product link")}</span><span><Mic2 size={16} aria-hidden="true" />{t("Nội dung tiếng Việt", "Vietnamese content")}</span><span><SlidersHorizontal size={16} aria-hidden="true" />{t("Phong cách của bạn", "Your own style")}</span><span><Film size={16} aria-hidden="true" />{t("Khung dọc & ngang", "Portrait & landscape")}</span>
      </div>
      <section id="quy-trinh" className="landing-process public-container" aria-labelledby="process-title">
        <div className="landing-section-heading"><div><p className="landing-eyebrow">{t("TỪ THÔNG TIN ĐẾN KHUNG HÌNH", "FROM INFORMATION TO FRAME")}</p><h2 id="process-title">{t("Một quy trình rõ ràng.", "A clear creative process.")}<br />{t("Để bạn tập trung sáng tạo.", "More room for your ideas.")}</h2></div><p>{t("Bạn giữ quyền quyết định nội dung. Reviewlab kết nối các bước trong cùng một không gian.", "You stay in control of the content. Reviewlab brings each step into one workspace.")}</p></div>
        <ol className="landing-steps">{steps.map(({ icon: Icon, title, text }, index) => <li key={title}><div className="step-top"><span className="step-icon"><Icon size={21} strokeWidth={1.5} aria-hidden="true" /></span><span className="step-number">0{index + 1}</span></div><h3>{title}</h3><p>{text}</p></li>)}</ol>
      </section>
      <section id="tinh-nang" className="landing-features public-container" aria-labelledby="features-title">
        <div className="landing-source-preview">
          <div className="source-sheet"><div className="source-sheet-heading"><span><FileCheck2 size={16} aria-hidden="true" />{t("Thông tin sản phẩm", "Product information")}</span><span className="source-demo-label">{t("Dữ liệu mẫu", "Sample data")}</span></div><div className="source-product-row"><div className="source-product-icon" aria-hidden="true"><div /></div><div><strong>Daily Bottle</strong><span>{t("Bình giữ nhiệt · Sản phẩm minh họa", "Insulated bottle · Sample product")}</span></div></div><dl><div><dt>{t("Mô tả", "Description")}</dt><dd>{t("Nhỏ gọn, đồng hành mỗi ngày.", "A compact everyday companion.")}</dd></div><div><dt>{t("Nguồn", "Source")}</dt><dd><Link2 size={12} aria-hidden="true" />example.com/daily-bottle</dd></div></dl><div className="source-confirmation"><Check size={14} aria-hidden="true" />{t("Bạn kiểm tra trước khi xác nhận", "You review before confirming")}</div></div>
          <p>{t("Thông tin rõ ràng. Câu chuyện có cơ sở.", "Clear information. A story with a foundation.")}</p>
        </div>
        <div className="landing-feature-copy"><p className="landing-eyebrow">{t("SÁNG TẠO CÓ CHỦ ĐÍCH", "CREATE WITH INTENTION")}</p><h2 id="features-title">{t("Sản phẩm là điểm bắt đầu.", "The product comes first.")}<br /><span>{t("Góc nhìn là của bạn.", "The perspective is yours.")}</span></h2><ul>
          <li><span>01</span><div><h3>{t("Hiểu sản phẩm trước khi kể", "Know the product before the story")}</h3><p>{t("Xem lại thông tin và nguồn tham khảo, chỉnh sửa những chi tiết cần thiết trước khi tạo nội dung.", "Check product details and references, and make your edits before creating content.")}</p></div></li>
          <li><span>02</span><div><h3>{t("Một sản phẩm, nhiều cách thể hiện", "One product, different expressions")}</h3><p>{t("Khám phá ba preset và hai khung hình 9:16, 16:9 để chọn cách kể phù hợp.", "Explore three presets and 9:16 or 16:9 formats to find the right expression.")}</p></div></li>
          <li><span>03</span><div><h3>{t("Giữ mọi thứ trong dự án", "Keep it together in a project")}</h3><p>{t("Sắp xếp thông tin, lựa chọn sáng tạo và kết quả video trong cùng không gian làm việc.", "Organize information, creative choices and video results in one workspace.")}</p></div></li>
        </ul></div>
      </section>
      <section id="price" className="landing-pricing public-container" aria-labelledby="price-title">
        <div className="landing-section-heading"><div><p className="landing-eyebrow">{t("BẢNG GIÁ · MINH HỌA", "PRICING · PREVIEW")}</p><h2 id="price-title">{t("Một không gian cho mỗi ý tưởng.", "Room for every idea.")}</h2></div><p>{t("Các gói và token dưới đây là dữ liệu mẫu. Giá chính thức và thanh toán chưa được triển khai.", "Plans and tokens below are sample data. Official pricing and payments are not available yet.")}</p></div>
        <div className="landing-price-grid">{initialStudio.plans.map(plan => <article className={`landing-price-card${plan.id === "creator" ? " is-featured" : ""}`} key={plan.id}><div className="landing-price-heading"><h3>{plan.name}</h3><span>{t("Gói mẫu", "Sample plan")}</span></div><p className="landing-price-amount">{number(plan.price)}<span>VND</span></p><p>{number(plan.tokens)} {t("token mẫu", "sample tokens")}</p><Link className={plan.id === "creator" ? "primary-button" : "landing-price-link"} href="/signup">{t("Khám phá bản xem thử", "Explore the preview")}<ArrowUpRight size={15} aria-hidden="true" /></Link></article>)}</div>
      </section>
      <section id="about" className="landing-about public-container" aria-labelledby="about-title"><div><p className="landing-eyebrow">ABOUT REVIEWLAB</p><h2 id="about-title">{t("Hiểu sản phẩm.", "Know the product.")}<br /><span>{t("Kể theo cách của bạn.", "Tell it your way.")}</span></h2></div><div><p>{t("Reviewlab là không gian hỗ trợ sáng tạo video review từ thông tin sản phẩm. Chúng tôi kết nối bước nhập link, kiểm tra nguồn và xác nhận nội dung với các lựa chọn sáng tạo trong cùng một quy trình.", "Reviewlab helps you create review videos from product information. We bring product links, source review, content confirmation and creative choices into one workflow.")}</p><p>{t("Bạn giữ quyền kiểm tra và chỉnh sửa thông tin trước khi tạo. Bản xem thử hiện tại giúp khám phá trải nghiệm bằng dữ liệu mẫu.", "You stay in control of reviewing and editing information before creating. The current preview lets you explore the experience with sample data.")}</p><Link href="/#quy-trinh">{t("Tìm hiểu quy trình", "Explore the workflow")}<ArrowRight size={15} aria-hidden="true" /></Link></div></section>
      <section className="landing-cta public-container" aria-labelledby="cta-title"><div><p className="landing-eyebrow">{t("CÂU CHUYỆN TIẾP THEO LÀ CỦA BẠN", "YOUR NEXT STORY STARTS HERE")}</p><h2 id="cta-title">{t("Bắt đầu với sản phẩm của bạn.", "Start with your product.")}</h2><p>{t("Trải nghiệm bản xem thử Reviewlab và khám phá luồng sáng tạo.", "Explore the Reviewlab preview and discover the creative workflow.")}</p></div><Link className="primary-button" href="/signup">{t("Tạo tài khoản xem thử", "Create a preview account")}<ArrowUpRight size={17} aria-hidden="true" /></Link></section>
      <p className="landing-disclosure public-container">{t("Phiên bản hiện tại mô phỏng luồng xử lý và kết quả bằng dữ liệu mẫu. Tài khoản lưu trên trình duyệt; chức năng tạo video bằng AI đang được phát triển.", "This preview simulates processing and results with sample data. Accounts are stored in your browser; AI video generation is in development.")}</p>
    </main>
  </PublicLayout>;
}
