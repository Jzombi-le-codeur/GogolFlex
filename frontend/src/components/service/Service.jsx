import "./Service.css";
import { useEffect, useState } from "react";

export default function Service({ name, description, getStatus, doAction }) {
    const [status, setStatus] = useState("Stopped");

    useEffect(() => {
        getStatus(name).then(status => {console.log(status); setStatus(status)});
    }, [name, getStatus]);

    return (
        <div className="service">
            <div className="service-informations">
                <p className="service-information service-status">{`STATUS : ${status}`}</p>
                <h2 className="service-information service-name">{name}</h2>
                <p className="service-information service-description">{description}</p>
            </div>
            <div className="service-actions">
                <button
                    className={`service-button main-button ${status.toLowerCase()} ${status === "Launching" ? "disabled" : ""}`}
                    onClick={ () => {
                        setStatus("Launching");
                        doAction(name, "Main", status).then(s => setStatus(s));
                    }}
                    disabled={status === "Launching"}
                >
                    {
                        status === "Stopped" || status === "Launching" || status === "Paused" ? (
                            <svg width="16" height="16" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                                <polygon
                                    points="30,20 75,50 30,80"
                                    fill="white"
                                    stroke="white"
                                    strokeWidth="12"
                                />
                            </svg>
                        ) : status === "Running" ? (
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
                                <rect x="6" y="4" width="4" height="16" rx="1"/>
                                <rect x="14" y="4" width="4" height="16" rx="1"/>
                            </svg>
                        ) : (
                            <svg></svg>
                        )
                    }
                </button>
                <button
                    className={`service-button stop-button ${status.toLowerCase()} ${status === "Stopped" || status === "Launching" ? "disabled" : ""}`}
                    onClick={ () => {
                        doAction(name, "Stop", status).then(s => setStatus(s));
                    }}
                    disabled={status === "Stopped" || status === "Launching"}
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="6" y="6" width="12" height="12" rx="2" fill="white"/>
                    </svg>
                </button>
            </div>
        </div>
    )
}