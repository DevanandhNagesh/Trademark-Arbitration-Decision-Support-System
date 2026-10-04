// auth-guard.js - Client-side authentication guard for protected DSS pages

export function requireAuth() {
    const token = sessionStorage.getItem("dss_jwt") || sessionStorage.getItem("dss_token");
    if (!token) {
        const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `auth.html?returnTo=${returnTo}`;
        return false;
    }
    return true;
}
