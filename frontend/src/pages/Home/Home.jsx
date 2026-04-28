import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Searchbar from "../../components/searchbar/Searchbar.jsx";
import "../../styles/home.css";

export default function Home() {
    const [query, setQuery] = useState("");

    const navigate = useNavigate();
    const search = (query) => {
        navigate(`/search?q=${query}`);
    }

    return (
        <div className="page search">
            {/*<h1 className="title title1"><a href="..">GogolFlex</a></h1>*/}
            <h1 className="title title2"><a href="..">GogolFlex</a></h1>
            <div className="main">
                <Searchbar search={search} query={query} setQuery={setQuery} />
            </div>
        </div>
    )
}