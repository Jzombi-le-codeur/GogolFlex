import "./Searchbar.css"

export default function Searchbar({ search, query, setQuery }) {
    return (
        <div className="search-bar">
            <div className="search-bar-input-box">
                <input
                    className="search-bar-input"
                    type="search" value={query}
                    onChange={(e) => {
                        setQuery(e.target.value)
                    }}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") {
                            search(query);
                        }
                    }}
                    />
            </div>
            <div className="search-bar-button-box">
                <button className="search-bar-button" onClick={() => search(query)}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                         fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <g transform="translate(-0.5, 2)">
                            <circle cx="11" cy="11" r="7"></circle>
                            <line x1="16.65" y1="16.65" x2="21" y2="21"></line>
                        </g>
                    </svg>
                </button>
            </div>
        </div>
    )
}