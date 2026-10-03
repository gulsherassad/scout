import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { Footer } from "./components/Footer";
import { MapPage } from "./pages/MapPage";
import { PlayerPage } from "./pages/PlayerPage";
import { SearchPage } from "./pages/SearchPage";

function NotFound() {
  return (
    <div className="page">
      <h1>Page not found</h1>
      <Link to="/">Back to search</Link>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <div className="shell">
        <nav className="topbar">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true" />
            scout
          </Link>
          <div className="nav-links">
            <NavLink to="/" end>
              Search
            </NavLink>
            <NavLink to="/map">Map</NavLink>
          </div>
        </nav>
        <main>
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/player/:id" element={<PlayerPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
