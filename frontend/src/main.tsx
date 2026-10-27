// Einstiegspunkt des Frontends.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { applyBrand } from "./brand";
import "./styles/theme.css";

applyBrand();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
