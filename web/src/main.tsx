import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/800.css";
import "@fontsource/bebas-neue/400.css";
import "./styles.css";
import "./vice.css";

// Android 15 affiche l'app sous la barre d'état : on réserve l'espace si le WebView ne le fournit pas
if ((window as any).Capacitor?.isNativePlatform?.()) document.documentElement.classList.add("native");
try { document.documentElement.dataset.theme = localStorage.getItem("theme") ?? "dark"; } catch { /* stockage indisponible */ }

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
);
