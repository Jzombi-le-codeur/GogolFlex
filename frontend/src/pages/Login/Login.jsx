import {useState} from "react";
import "../../styles/login.css";
import {useNavigate, useSearchParams} from "react-router-dom";

export default function Login({ setAccessToken }) {
    const [searchParams] = useSearchParams();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");

    const navigate = useNavigate();

    const sendIds = () => {
        fetch("/api/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({"username": username, "password": password}),
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "Connected") {
                setMessage("Connected");
                setAccessToken(data.accessToken);
                if (searchParams.get("redirect")) {
                    navigate(`/${searchParams.get("redirect")}`);
                }
            } else if (data.status === "Incorrect") {
                setMessage("Password Incorrect!");
                setPassword("");
            } else if (data.status === "NotExists") {
                setMessage("User does not exist!");
                setUsername("");
                setPassword("");
            } else {
                console.log("rien");
            }
        })
        .catch(() => setMessage("Error"));
    }

    return (
        <div className="page login">
            <div className="login-form">
                <h2 className="login-title">Login</h2>
                <p className={`message ${message ? "" : "disabled"}`}>{message}</p>
                {/* Username */}
                <div
                    className="username"
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && username && password) {
                            sendIds()
                        }
                    }}
                >
                    <label className="username-label" htmlFor="username">Username</label>
                    <input
                        className="username-input"
                        id="username"
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                </div>

                {/* Password */}
                <div
                    className="password"
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && username && password) {
                            sendIds()
                        }
                    }}
                >
                    <label className="password-label" htmlFor="password">Password</label>
                    <input
                        className="password-input"
                        id="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                </div>

                {/* Send */}
                <button
                    onClick={() => {
                        console.log(username, password);
                        sendIds();
                    }}
                    disabled={!username || !password}
                >
                    Login
                </button>
            </div>
        </div>
    )
}