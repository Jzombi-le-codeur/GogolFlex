import {useState} from "react";
import "./Searchbar.css"

export default function Searchbar() {
    const [request, setRequest] = useState("");
    return (
        <div className="search-bar">
            <div className="search-bar-input-box">
                <input className="search-bar-input" type="text" value={request} onChange={(e) => {setRequest(e.target.value)}}/>
            </div>
            <div className="search-bar-button-box">
                <button className="search-bar-button">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                         fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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