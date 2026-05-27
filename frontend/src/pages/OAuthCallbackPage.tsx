import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { oauthCallback } from "../api/authApi";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function OAuthCallbackPage() {
  const { provider } = useParams<{ provider: string }>();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { reloadUser } = useAuth();
  const [status, setStatus] = useState("Completing OAuth login...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      if (provider !== "google" && provider !== "github") {
        setError("Unsupported OAuth provider.");
        return;
      }

      const code = params.get("code");
      const state = params.get("state");
      if (!code || !state) {
        setError("Missing OAuth callback parameters.");
        return;
      }

      try {
        await oauthCallback(provider, code, state);
        const user = await reloadUser();
        if (!user) {
          throw new Error("Failed to load user after OAuth login");
        }
        navigate(user.role === "admin" ? "/admin" : "/user", { replace: true });
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "OAuth callback failed");
      }
    };

    void run();
  }, [provider, params, navigate, reloadUser]);

  return (
    <div className="screen center">
      <div className="status-card">
        <h2>OAuth Callback</h2>
        {error ? <p className="feedback error">{error}</p> : <p>{status}</p>}
      </div>
    </div>
  );
}
