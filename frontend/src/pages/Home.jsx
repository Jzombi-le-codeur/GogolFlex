import Searchbar from "../components/searchbar/Searchbar";
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";

export default function Home() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [results, setResults] = useState([]);
    const [query, setQuery] = useState("");

    const search = (query) => {
        fetch("http://localhost:8000/search", {
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
    }

    useEffect(() => {
        const q = searchParams.get("q");
        if (q) {
            setQuery(q);
            search(q);
        }
    }, [searchParams, search]);

    return (
        <div className={`page${results.length > 0 ? " display-results" : ""}`}>
            <h1 className={`title${results.length > 0 ? " display-results" : ""}`}><a href=".">GogolFlex</a></h1>
            <div className={`main${results.length > 0 ? " display-results" : ""}`}>
                <Searchbar search={search} query={query} setQuery={setQuery} />
                {results.length > 0 ? (
                    <div className="results">
                        {
                            results.map((result) => (
                                <div className="result">
                                    <h3 className="result-title"><a href={result.url}>{result.title}</a></h3>
                                    <p className="result-url">{result.url}</p>
                                </div>
                            ))
                        }
                    </div>
                ) : null}
            </div>
        </div>
    )
}