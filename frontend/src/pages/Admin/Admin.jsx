import "../../styles/admin.css";
import Service from "../../components/service/Service";
import {useState} from "react";

export default function Admin() {
    const [services, setServices] = useState([
        {
            "name": "Crawler",
            "description": "Explore the web to find new webpages",
            "status": "Paused"
        },
        {
            "name": "Parser",
            "description": "Parse found page's informations",
            "status": "Paused"
        },
        {
            "name": "Indexer",
            "description": "Save found pages in GogolFlex's Database",
            "status": "Paused"
        },
    ]);

    const changeStatus = (name, status) => {
        setServices(
            prev =>
                prev.map(service => (
                    service.name === name ? { ...service, status: status } : service
                ))
        )
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