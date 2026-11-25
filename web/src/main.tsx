import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

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
