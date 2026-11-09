import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { RepoProvider } from "./context/RepoContext.jsx";
import "./styles/theme.css";
import "./styles/global.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <RepoProvider>
        <App />
      </RepoProvider>
    </BrowserRouter>
  </StrictMode>,
);