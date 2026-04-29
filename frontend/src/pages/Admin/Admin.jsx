import "../../styles/admin.css";
import Service from "../../components/service/Service.jsx";
import {useState, useCallback} from "react";

export default function Admin() {
    const [services] = useState([
        {
            "name": "Crawler",
            "description": "Explore the web to find new webpages",
        },
        {
            "name": "Parser",
            "description": "Parse found page's informations",
        },
        {
            "name": "Indexer",
            "description": "Save found pages in GogolFlex's Database",
        },
    ]);

    const getStatus = useCallback((name) => {
        const url = "/api/get-status";

        return fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({"name": name}),
        })
        .then(res => res.json())
        .then(data => data.status ?? "Stopped")
        .catch(() => "Stopped");
    }, [])

    const askUntilReady = useCallback((name) => {
        return new Promise((resolve) => {
            const interval = setInterval(() => {
                getStatus(name).then((status) => {
                    if (status !== "Stopped" && status !== "Launching") {
                        clearInterval(interval);
                        const status = fetch("/api/start", {
                            method: "POST",
                            headers: {"Content-Type": "application/json"},
                            body: JSON.stringify({"name": name}),
                        })
                            .then(res => res.json())
                            .then(data => data.status ?? "Stopped")
                            .catch(() => "Stopped");
                        resolve(status);
                    } else if (status === "Stopped") {
                        clearInterval(interval);
                        resolve("Stopped");
                    }
                });
            }, 1000);
        });
    }, [getStatus]);

    const doAction = (name, button, status) => {
        // Get API's url
        if (button === "Main") {
            if (status === "Paused") {
                return fetch("/api/start", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"name": name}),
                })
                    .then(res => res.json())
                    .then(data => data.status ?? "Stopped")
                    .catch(() => "Stopped");
            }  else if (status === "Running") {
                return fetch("/api/pause", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"name": name}),
                })
                    .then(res => res.json())
                    .then(data => data.status ?? "Stopped")
                    .catch(() => "Stopped");
            } else {
                return fetch("/api/run", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"name": name}),
                })
                    .then(res => res.json())
                    .then(data => {
                        const status = data.status ?? "Stopped";
                        if (status === "Launching") {
                            return askUntilReady(name);
                        }
                        return status;
                    })
                    .catch(() => "Stopped");
            }
        } else if (button === "Stop") {
            if (status !== "Stopped") {
                return fetch("/api/stop", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"name": name}),
                })
                    .then(res => res.json())
                    .then(data => data.status ?? "Stopped")
                    .catch(() => "Stopped");
            } else {
                return "Stopped";
            }
        }
    }

    return (
        <div className="page admin">
            <header className="admin">
                <h1 className="title admin">GogolFlex</h1>
                <p className="sub-title admin">Admin</p>
            </header>
            <main className="admin">
                <h2>Services</h2>
                <div className="services admin">
                    {
                        services.map((service, index) => (
                            <Service
                                key={index}
                                key={index}
                                name={service.name}
                                description={service.description}
                                getStatus={getStatus}
                                doAction={doAction}
                            />
                        ))
                    }
                </div>
            </main>
        </div>
    )
}