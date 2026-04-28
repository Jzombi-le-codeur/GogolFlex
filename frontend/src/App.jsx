import Home from "./pages/Home/Home.jsx";
import "./styles/main.css";
import {BrowserRouter, Routes, Route} from "react-router-dom";
import Results from "./pages/Results/Results.jsx";
import Admin from "./pages/Admin/Admin.jsx";
import Error from "./pages/Error/Error.jsx";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/search" element={<Results />} />
                <Route path="/admin" element={<Admin />} />
                <Route path="*" element={<Error code={404} />} />
            </Routes>
        </BrowserRouter>
    )
}