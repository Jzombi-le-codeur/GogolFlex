import Home from "./pages/Home/Home.jsx";
import "./styles/main.css";
import {BrowserRouter, Routes, Route} from "react-router-dom";
import Results from "./pages/Results/Results.jsx";
import Admin from "./pages/Admin/Admin.jsx";
import Error from "./pages/Error/Error.jsx";
import Login from "./pages/Login/Login.jsx";
import {useState} from "react";

export default function App() {
    const [accessToken, setAccessToken] = useState("");
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/search" element={<Results />} />
                <Route path="/login" element={<Login accessToken={accessToken} setAccessToken={setAccessToken} />} />
                <Route path="/admin" element={<Admin accessToken={accessToken} setAccessToken={setAccessToken} />} />
                <Route path="*" element={<Error code={404} />} />
            </Routes>
        </BrowserRouter>
    )
}