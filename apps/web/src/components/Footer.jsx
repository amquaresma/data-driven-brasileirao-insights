// Preencha com o endereço completo do seu perfil, por exemplo "https://www.linkedin.com/in/seu-usuario".
// Enquanto estiver vazio, o link do LinkedIn não aparece.
const LINKEDIN_URL = "https://www.linkedin.com/in/matheus-quaresma-/";
const GITHUB_URL = "https://github.com/amquaresma";

export function Footer() {
  return (
    <footer className="site-footer">
      <p>
        <span>© 2026 · Feito por </span>
        <strong>Matheus Quaresma</strong>
      </p>
      <nav className="site-footer-links" aria-label="Contato">
        <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
        {LINKEDIN_URL && (
          <a href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer">
            LinkedIn
          </a>
        )}
      </nav>
      <p className="site-footer-note">
        Projeto educacional, sem vínculo com CBF, ge ou Highlightly. As previsões não são recomendação
        de aposta.
      </p>
    </footer>
  );
}
