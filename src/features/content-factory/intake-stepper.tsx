export function IntakeStepper({ current }: { current: 1 | 2 | 3 }) {
  return (
    <ol
      className="flow-steps onboarding-steps"
      aria-label="Tiến trình onboarding"
    >
      {["Nhập thông tin", "Thu thập dữ liệu", "Review PKB"].map(
        (label, index) => (
          <li
            key={label}
            aria-current={index + 1 === current ? "step" : undefined}
          >
            <span>0{index + 1}</span>
            {label}
          </li>
        ),
      )}
    </ol>
  );
}
