import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import PhoneOnly from "./components/PhoneOnly.jsx";
import "./style.css";

const Root = window.location.pathname.startsWith("/phone") ? PhoneOnly : App;
createRoot(document.getElementById("root")).render(<Root />);
