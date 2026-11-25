import { Link } from "react-router-dom";
import { Settings } from "lucide-react";

/** Palmier stylisé (silhouette), dessiné à la main. */
function Palm({ x, s, flip = false }: { x: number; s: number; flip?: boolean }) {
  return (
    <g transform={`translate(${x} 250) scale(${flip ? -s : s} ${s})`} fill="#140a24">
      <path d="M-4 0 C-2 -60 6 -110 14 -150 L20 -150 C12 -108 6 -60 6 0 Z" />
      <path d="M16 -150 C-10 -170 -40 -160 -62 -130 C-38 -150 -12 -152 14 -142 Z" />
      <path d="M16 -150 C0 -185 -30 -195 -56 -186 C-28 -180 -8 -170 12 -146 Z" />
      <path d="M18 -150 C30 -188 58 -196 80 -180 C56 -178 36 -170 22 -146 Z" />
      <path d="M18 -150 C46 -164 78 -152 96 -122 C72 -142 46 -148 22 -144 Z" />
      <path d="M17 -150 C14 -178 22 -200 40 -212 C30 -192 26 -172 22 -148 Z" />
    </g>
  );
}

export default function ViceHero({ subtitle }: { subtitle: string }) {
  return (
    <div className="vc-hero">
      <svg className="scene" viewBox="0 0 400 250" preserveAspectRatio="xMidYMax slice" aria-hidden>
        <defs>
          <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ffe08a" /><stop offset=".55" stopColor="#ff9a3d" /><stop offset="1" stopColor="#ff3d8b" />
          </linearGradient>
          <clipPath id="sunclip"><circle cx="270" cy="150" r="74" /></clipPath>
        </defs>
        {/* soleil rétro à bandes */}
        <g clipPath="url(#sunclip)">
          <rect x="190" y="70" width="160" height="160" fill="url(#sun)" />
          {[0, 1, 2, 3, 4, 5].map((i) => <rect key={i} x="190" y={152 + i * 11} width="160" height={2 + i * 1.4} fill="#c2307c" />)}
        </g>
        {/* mer et reflets */}
        <rect x="0" y="200" width="400" height="50" fill="#2a0e4d" opacity=".85" />
        {[0, 1, 2, 3].map((i) => <rect key={i} x={230 - i * 8} y={206 + i * 9} width={80 + i * 16} height="2" fill="#ff9a3d" opacity={0.8 - i * 0.15} rx="1" />)}
        {/* skyline lointaine */}
        <path d="M0 200 L0 182 L18 182 L18 170 L30 170 L30 186 L44 186 L44 160 L52 154 L60 160 L60 188 L78 188 L78 176 L92 176 L92 200 Z" fill="#3b1463" opacity=".9" />
        <path d="M330 200 L330 178 L342 178 L342 162 L352 162 L352 180 L368 180 L368 170 L384 170 L384 186 L400 186 L400 200 Z" fill="#3b1463" opacity=".9" />
        <Palm x={60} s={0.95} /><Palm x={112} s={0.7} flip /><Palm x={372} s={1.05} flip />
      </svg>
      <Link to="/reglages" className="chip vc-settings"><Settings size={15} /> Réglages</Link>
      <div className="vc-title"><b>GTA</b><span>{subtitle}</span></div>
    </div>
  );
}
