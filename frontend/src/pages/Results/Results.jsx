import React from "react";
import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import Searchbar from "../../components/searchbar/Searchbar.jsx";
import "../../styles/results.css";

export default function Results() {
    const [searchParams] = useSearchParams();
    const [results, setResults] = useState([]);
    const [query, setQuery] = useState("");

    const doSearch = useCallback(query => {
        fetch(`/api/search`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({"query": query, n_results: 20})
        })
            .then(res => res.json())
            .then(data => {
                setResults(data.results);
            })
            .catch(err => console.log(err));
    }, [])

    const navigate = useNavigate();
    const search = (query) => {
        navigate(`/search?q=${query}`);
    }

    useEffect(() => {
        const q = searchParams.get("q");
        if (q) {
            setQuery(q);
            doSearch(q);
        }
    }, [searchParams, doSearch]);

    return (
        <div className="page display-results">
            <h1 className="title display-results"><a href="..">GogolFlex</a></h1>
            <div className="main display-results">
                <Searchbar search={search} query={query} setQuery={setQuery} />
                <React.Fragment>
                    <p className="message">{
                        results.length === 0 ? "No results found" :
                            results.length === 1 ? "1 result found" :
                                `${results.length} results found`
                    }</p>
                    <div className="results">
                        {
                            results.length > 0 ? (
                                results.map((result, index) => (
                                    <div key={`result-${index}`} className="result">
                                        <h3 className="result-title"><a href={result.url}>{result.title}</a></h3>
                                        <p className="result-url">{result.url}</p>
                                    </div>
                                ))
                            ) : null
                        }
                    </div>
                </React.Fragment>
            </div>
        </div>
    )
}