import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// Intercept double-click event to prevent development tools (like lovable-tagger) from opening typing/inspect panels
if (import.meta.env.DEV) {
  window.addEventListener(
    "dblclick",
    (e) => {
      e.stopImmediatePropagation();
    },
    { capture: true }
  );
}

createRoot(document.getElementById("root")!).render(<App />);
