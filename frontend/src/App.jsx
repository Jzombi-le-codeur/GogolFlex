import Home from "./pages/Home/Home";
import "./styles/main.css";
import {BrowserRouter, Routes, Route} from "react-router-dom";
import Results from "./pages/Results/Results";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/search" element={<Results />} />
            </Routes>
        </BrowserRouter>
    )
}