import "@fontsource-variable/onest";
import { MotionConfig } from "motion/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AppRoutes } from "./app/router";
import { BrokerSessionProvider } from "./broker/BrokerSessionProvider";
import "./features/detail/feedback-editor.css";
import "./styles/tokens.css";
import "./styles/global.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element is missing");

createRoot(root).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <BrokerSessionProvider>
        <HashRouter>
          <AppShell>
            <AppRoutes />
          </AppShell>
        </HashRouter>
      </BrokerSessionProvider>
    </MotionConfig>
  </StrictMode>,
);
