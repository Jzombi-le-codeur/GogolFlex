import Searchbar from "../components/searchbar/Searchbar";
import {useState} from "react";

export default function Home() {
    const [results, setResults] = useState(false);
    const [request, setRequest] = useState("");

    return (
        <div className={`page${results ? " display-results" : ""}`}>
            <h1 className={`title${results ? " display-results" : ""}`}><a href=".">GogolFlex</a></h1>
            <div className={`main${results ? " display-results" : ""}`}>
                <Searchbar results={results} setResults={setResults} request={request} setRequest={setRequest} />
                {results ? (
                    <div className="results">
                        <div className="result">
                            <h3 className="result-title"><a href="https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal">Wikipédia</a></h3>
                            <p className="result-url">https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal</p>
                        </div>
                        <div className="result">
                            <h3 className="result-title"><a href="https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal">Wikipédia</a></h3>
                            <p className="result-url">https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal</p>
                        </div>
                    </div>
                ) : null}
            </div>
        </div>
    )
}