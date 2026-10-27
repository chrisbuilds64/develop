import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./tokens.css";
import "./app.css";
import { App } from "./App";
import { Director } from "./components/Director";
import { initPresenting } from "./moments";

initPresenting();

const client = new QueryClient({ defaultOptions: { queries: { refetchInterval: 25_000, refetchOnWindowFocus: true, retry: 1, staleTime: 5_000 } } });

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <App />
      <Director />
    </QueryClientProvider>
  </React.StrictMode>,
);
