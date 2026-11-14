import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import PhoneOnly from "./components/PhoneOnly.jsx";
import TestPage from "./components/TestPage.jsx";
import "./style.css";

const path = window.location.pathname;
const Root = path.startsWith("/phone") ? PhoneOnly : path.startsWith("/test") ? TestPage : App;
createRoot(document.getElementById("root")).render(<Root />);
