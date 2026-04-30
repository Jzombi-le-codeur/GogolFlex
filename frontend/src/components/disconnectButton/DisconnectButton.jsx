import {useLocation, useNavigate} from "react-router-dom";
import "./DisconnectButton.css"

export default function DisconnectButton({ username, setAccessToken }) {
    const location = useLocation();
    const navigate = useNavigate();
    return (
        <p
            className="disconnect-button"
            onClick={() => {
                fetch("/api/logout", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({"username": username}),
                })
                setAccessToken("");
                !["/", "/results"].includes(location.pathname) ? navigate("/") : null;
            }}
        >
            Disconnect
        </p>
    )
}