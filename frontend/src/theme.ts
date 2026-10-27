// Farben für Diagramme. Recharts zeichnet SVG und braucht feste Farbwerte,
// daher stehen sie hier zusätzlich zu den CSS-Variablen in theme.css.
//
// Die drei Reihenfarben wurden auf Unterscheidbarkeit bei Farbsehschwäche und
// Kontrast zum dunklen Hintergrund geprüft. Statusfarben (gelb/rot) sind für
// Grenzwerte reserviert und werden nie für normale Datenreihen benutzt.

export const CHART = {
  series: ["#3987e5", "#d95926", "#199e70"], // blau, orange, türkis
  grid: "#262a31",
  axis: "#3a3f47",
  tick: "#8b929c",
  eclipse: "rgba(255, 255, 255, 0.06)",
};

export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  critical: "#d03b3b",
};
