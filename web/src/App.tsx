import { BookOpen, CarFront, House, Map as MapIcon, MessageCircle } from "lucide-react";
import { useEffect } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { App as CapApp } from "@capacitor/app";
import { runBackHandlers } from "./back";
import { autoConnect } from "./connect";
import Home from "./pages/Home";
import Catalog from "./pages/Catalog";
import VehicleDetailPage from "./pages/VehicleDetail";
import Compare from "./pages/Compare";
import Encyclopedia from "./pages/Encyclopedia";
import MapPage from "./pages/MapPage";
import Assistant from "./pages/Assistant";
import Settings from "./pages/Settings";
import EntityPage from "./pages/EntityPage";

const NAV = [
  { to: "/", label: "Accueil", Icon: House, end: true },
  { to: "/carte", label: "Carte", Icon: MapIcon },
  { to: "/vehicules", label: "Véhicules", Icon: CarFront },
  { to: "/encyclopedie", label: "Encyclopédie", Icon: BookOpen },
  { to: "/assistant", label: "Assistant", Icon: MessageCircle },
];

export default function App() {
  const nav = useNavigate();
  const loc = useLocation();
  // Bouton retour Android : ferme d'abord un panneau ouvert, sinon revient à l'écran précédent,
  // et ne quitte l'appli (mise en arrière-plan) que depuis l'accueil.
  useEffect(() => {
    if (!(window as any).Capacitor?.isNativePlatform?.()) return;
    const h = CapApp.addListener("backButton", () => {
      if (runBackHandlers()) return;
      if (window.location.hash.replace("#", "") !== "/" && window.location.hash !== "") nav(-1);
      else CapApp.minimizeApp();
    });
    return () => { h.then((x) => x.remove()); };
  }, [nav, loc.pathname]);
  // Chez soi : le téléphone trouve le PC tout seul sur le Wi-Fi et récupère les données de la nuit
  useEffect(() => {
    (window as any).__autoConnect = autoConnect;   // utilisé par les tests et le bouton « Rechercher le PC »
    if (!(window as any).Capacitor?.isNativePlatform?.()) return;   // navigateur sur le PC : déjà connecté
    autoConnect((st) => { (window as any).__pcState = st; window.dispatchEvent(new Event("pcstate")); });
  }, []);
  return (
    <div className="app">
      <div className="statusbar-bg" aria-hidden />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/carte" element={<MapPage />} />
        <Route path="/vehicules" element={<Catalog kind="vehicle" key="v" />} />
        <Route path="/vehicules/comparer" element={<Compare />} />
        <Route path="/vehicules/:id" element={<VehicleDetailPage />} />
        <Route path="/encyclopedie" element={<Encyclopedia />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/reglages" element={<Settings />} />
        <Route path="/fiche/:id" element={<EntityPage />} />
        <Route path="/armes" element={<Catalog kind="weapon" key="w" />} />
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
