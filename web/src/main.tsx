import "@fontsource-variable/onest";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AppRoutes } from "./app/router";
import "./styles/tokens.css";
import "./styles/global.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element is missing");

createRoot(root).render(
  <StrictMode>
    <HashRouter>
      <AppShell>
        <AppRoutes />
      </AppShell>
    </HashRouter>
  </StrictMode>,
);
