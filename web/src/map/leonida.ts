import L from "leaflet";

/**
 * Géométrie du fond de carte gtadb.org (GTA VI, jeu de tuiles « day ») :
 * monde de 32 768 unités de jeu = 1 024 px au zoom 0, origine décalée de 16 384.
 * En CRS.Simple de Leaflet : lng = px, lat = -py.
 */
export const WORLD = 32768;
export const ZERO = 16384;
const K = 1024 / WORLD;

export const gameToLatLng = (x: number, y: number): L.LatLngExpression => [-(ZERO - y) * K, (x + ZERO) * K];
export const latLngToGame = (ll: L.LatLng): [number, number] => [ll.lng / K - ZERO, ZERO + ll.lat / K];

// Emprise des tuiles disponibles (zoom 0 : x 0..2, y 0..3 tuiles de 256 px)
export const TILE_BOUNDS = L.latLngBounds([-(4 * 256), 0], [0, 3 * 256]);
// Emprise utile (île + Keys), pour le cadrage initial
export const LEONIDA_BOUNDS = L.latLngBounds(gameToLatLng(-9000, -11500) as L.LatLngTuple, gameToLatLng(6500, 9500) as L.LatLngTuple);

/** Tuiles embarquées z0-6 (gtadb n'existe pas au-delà du zoom 6). */
export function createTileLayer(serverBase: string): L.TileLayer {
  const Layer = L.TileLayer.extend({
    getTileUrl(this: L.TileLayer, c: L.Coords) {
      const z = c.z;
      if (z <= 5) return `tiles/day/${z}/${z},${c.y},${c.x}.jpg`;
      return `tiles/day/6/6,${c.y},${c.x}.webp`;   // zoom 6 embarqué (WebP) : net même hors ligne
    },
  });
  return new (Layer as unknown as new (u: string, o: L.TileLayerOptions) => L.TileLayer)("", {
    tileSize: 256, minZoom: 0, maxNativeZoom: 6, maxZoom: 7,   // 7 : arrondi du zoom 6,5 de la carte (sinon les tuiles disparaissent)
    bounds: TILE_BOUNDS, noWrap: true, keepBuffer: 4,
    attribution: 'Fond de carte © <a href="https://gtadb.org">gtadb.org</a> (CC BY 4.0)',
  });
}

export const distance = (a: [number, number], b: [number, number]) => Math.hypot(a[0] - b[0], a[1] - b[1]);
