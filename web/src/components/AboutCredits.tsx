const TMDB_LOGO = "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_1-5bdc75aaebeb75dc7ae79426ddd9be3b2be1e342510f8202baf6bffa71d7f5c4.svg";

export function AboutCredits() {
  return (
    <footer className="site-credits" aria-labelledby="credits-title">
      <div>
        <h2 id="credits-title">О проекте</h2>
        <p>Личная медиатека и рекомендации на основе нашей истории просмотров.</p>
      </div>
      <div className="tmdb-credit">
        <a href="https://www.themoviedb.org" target="_blank" rel="noreferrer" aria-label="TMDB — The Movie Database">
          <img src={TMDB_LOGO} alt="TMDB" />
        </a>
        <p>This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
      </div>
    </footer>
  );
}
