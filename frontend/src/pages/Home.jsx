import Searchbar from "../components/searchbar/Searchbar";
import {useState} from "react";

export default function Home() {
    const [request, setRequest] = useState()
    return (
        <div className="page">
            <div className="search">
                <h1 className="title">GogolFlex</h1>
                <Searchbar />
            </div>
        </div>
    )
}