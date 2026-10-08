export function Footer() {
  return (
    <footer className="factory-footer workspace-footer">
      <span>© {new Date().getFullYear()} Reviewlab. All rights reserved.</span>
      <nav aria-label="Liên kết bên ngoài">
        <a href="https://github.com/PotatoMine725/AI-review-FE" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
        <a href="https://github.com/PotatoMine725/AI-review-BE/tree/dev/docs" target="_blank" rel="noopener noreferrer">Tài liệu ↗</a>
      </nav>
    </footer>
  );
}
