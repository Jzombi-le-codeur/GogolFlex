import {useState} from "react";
import "./PageAdder.css"

export default function PageAdder({ crawlerStatus }) {
    const [pageUrl, setPageUrl] = useState("");
    const [errorMessage, setErrorMessage] = useState("");

    const addSite = () => {
        setErrorMessage("");
        fetch("/api/add-page", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({"url": pageUrl})
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "nourl") {
                setErrorMessage("Please enter an URL")
            }
        })
        .catch(err => console.log(err));
    }

    return (
        <div
            className="pageAdder"
        >
            <div className="input-box">
                <p className={`error-message ${errorMessage ? "" : "hidden"}`}>{errorMessage}</p>
                <input
                    className="pageAdder-input"
                    type="text"
                    placeholder="Enter a page's url..."
                    value={pageUrl}
                    onChange={(e) => {setPageUrl(e.target.value)}}
                />
            </div>
            <button
                className={`button pageAdder-button ${crawlerStatus === "Running" || !pageUrl ? "disabled" : ""}`}
                onClick={() => addSite()}
                disabled={crawlerStatus === "Running" || !pageUrl}
            >Add page to queue</button>
        </div>
    )
}