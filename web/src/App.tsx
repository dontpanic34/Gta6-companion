import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import Vehicles from "./pages/Vehicles";
import VehicleDetailPage from "./pages/VehicleDetail";
import Compare from "./pages/Compare";
import Encyclopedia from "./pages/Encyclopedia";
import MapPage from "./pages/MapPage";
import Assistant from "./pages/Assistant";
import Settings from "./pages/Settings";
import EntityPage from "./pages/EntityPage";

const I = {
  home: <path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />,
  map: <path d="M9 4l6 2 6-2v16l-6 2-6-2-6 2V6zM9 4v16M15 6v16" />,
  car: <path d="M5 16h14M3 16v-3l2-5h14l2 5v3h-2a2 2 0 0 1-4 0H9a2 2 0 0 1-4 0zM7 16a2 2 0 1 0 0 .1M17 16a2 2 0 1 0 0 .1" />,
  book: <path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 21V5M8 7h7" />,
  chat: <path d="M4 5h16v11H9l-5 4z" />,
};
const Icon = ({ d }: { d: JSX.Element }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);

export default function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/carte" element={<MapPage />} />
        <Route path="/vehicules" element={<Vehicles />} />
        <Route path="/vehicules/comparer" element={<Compare />} />
        <Route path="/vehicules/:id" element={<VehicleDetailPage />} />
        <Route path="/encyclopedie" element={<Encyclopedia />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/reglages" element={<Settings />} />
        <Route path="/fiche/:id" element={<EntityPage />} />
      </Routes>
      <nav className="nav">
        <NavLink to="/" end><Icon d={I.home} />Accueil</NavLink>
        <NavLink to="/carte"><Icon d={I.map} />Carte</NavLink>
        <NavLink to="/vehicules"><Icon d={I.car} />Véhicules</NavLink>
        <NavLink to="/encyclopedie"><Icon d={I.book} />Encyclopédie</NavLink>
        <NavLink to="/assistant"><Icon d={I.chat} />Assistant</NavLink>
      </nav>
    </div>
  );
}
