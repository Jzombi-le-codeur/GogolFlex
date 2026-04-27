import "../../styles/admin.css";
import Service from "../../components/service/Service";
import {useState, useCallback} from "react";

export default function Admin() {
    const [services, setServices] = useState([
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
        const host = process.env[`REACT_APP_${name.toUpperCase()}_API_HOST`]
        const port = process.env[`REACT_APP_${name.toUpperCase()}_API_PORT`]
        const url = `http://${host}:${port}/get-status`;

        return fetch(url, {
            method: "GET",
        })
        .then(res => res.json())
        .then(data => data.status ?? "Stopped")
        .catch(err => "Stopped");
    }, [])

    const doAction = (name, button) => {
        // Get status
        return getStatus(name).then(status => {

            // Get API's url
            if (status === "Stopped") {
                return fetch(`http://${process.env.REACT_APP_API_HOST}:${process.env.REACT_APP_API_PORT}/run-service`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"name": name}),
                })
                    .then(res => res.json())
                    .then(data => data.status ?? "Stopped")
                    .catch(err => "Stopped");
            } else {
                const host = process.env[`REACT_APP_${name.toUpperCase()}_API_HOST`]
                const port = process.env[`REACT_APP_${name.toUpperCase()}_API_PORT`]
                let action = ""
                if (button === "Main") {
                    if (status === "Paused") {
                        action = "start"
                    } else {
                        action = "pause"
                    }
                } else {
                    action = "stop"
                }

                const url = `http://${host}:${port}/${action}`;

                // Request to API
                return fetch(url, {
                    method: "GET",
                })
                    .then(res => res.json())
                    .then(data => data.status ?? "Stopped")
                    .catch(err => "Stopped");
            }
        });
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