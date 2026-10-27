// ★ Zentrale Stelle für Produktname und Akzentfarbe.
// Hier ändern – der Rest der Oberfläche übernimmt die Werte automatisch.

export const BRAND = {
  name: "OrbitDesk",
  tagline: "Mission control for small satellites",
  // Akzentfarbe für Logo, aktive Tabs, Buttons, Fokusrahmen
  accent: "#3987e5",
  // Textfarbe auf Flächen in Akzentfarbe (muss gut lesbar sein)
  accentText: "#ffffff",
};

/** Überträgt die Brand-Werte in CSS-Variablen und den Fenstertitel. */
export function applyBrand(): void {
  const root = document.documentElement.style;
  root.setProperty("--accent", BRAND.accent);
  root.setProperty("--accent-text", BRAND.accentText);
  document.title = BRAND.name;
}
