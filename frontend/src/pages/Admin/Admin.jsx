import "../../styles/admin.css";
import Service from "../../components/service/Service";
import {useState} from "react";

export default function Admin() {
    const [services, setServices] = useState([
        {
            "name": "Crawler",
            "description": "Explore the web to find new webpages",
            "status": "Stopped"
        },
        {
            "name": "Parser",
            "description": "Parse found page's informations",
            "status": "Stopped"
        },
        {
            "name": "Indexer",
            "description": "Save found pages in GogolFlex's Database",
            "status": "Stopped"
        },
    ]);

    const changeStatus = (name, status) => {
        let error = false;

        // Get API's url
        const host = process.env[`REACT_APP_${name.toUpperCase()}_API_HOST`]
        const port = process.env[`REACT_APP_${name.toUpperCase()}_API_PORT`]
        const action = status === "Running" ? "start" : status === "Paused" ? "stop" : "shutdown";
        const url = `http://${host}:${port}/${action}`;

        // Request to API
        fetch(url, {
            method: "GET",
        })
        .then(res => res.json())
        .then(data => {console.log(data)})
        .catch(err => error = true);

        // Update service
        if (!error) {
            setServices(
                prev =>
                    prev.map(service => (
                        service.name === name ? { ...service, status: status } : service
                    ))
            )
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
                                name={service.name}
                                description={service.description}
                                status={service.status}
                                changeStatus={changeStatus}
                            />
                        ))
                    }
                </div>
            </main>
        </div>
    )
}