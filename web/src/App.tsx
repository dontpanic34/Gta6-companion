import { BookOpen, CarFront, House, Map as MapIcon, MessageCircle } from "lucide-react";
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
import Weapons from "./pages/Weapons";

const NAV = [
  { to: "/", label: "Accueil", Icon: House, end: true },
  { to: "/carte", label: "Carte", Icon: MapIcon },
  { to: "/vehicules", label: "Véhicules", Icon: CarFront },
  { to: "/encyclopedie", label: "Encyclopédie", Icon: BookOpen },
  { to: "/assistant", label: "Assistant", Icon: MessageCircle },
];

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
        <Route path="/armes" element={<Weapons />} />
        <Route path="/armes/:id" element={<VehicleDetailPage />} />
      </Routes>
      <nav className="nav">
        {NAV.map(({ to, label, Icon, end }) => (
          <NavLink key={to} to={to} end={end}><Icon size={24} strokeWidth={1.8} />{label}</NavLink>
        ))}
      </nav>
    </div>
  );
}
