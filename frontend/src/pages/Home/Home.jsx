import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Searchbar from "../../components/searchbar/Searchbar";

export default function Home() {
    const [query, setQuery] = useState("");

    const navigate = useNavigate();
    const search = (query) => {
        navigate(`/search?q=${query}`);
    }

    return (
        <div className="page">
            <h1 className="title"><a href="..">GogolFlex</a></h1>
            <div className="main">
                <Searchbar search={search} query={query} setQuery={setQuery} />
            </div>
        </div>
    )
}