// auth.js - Client-side authentication handling

const TOKEN_KEY = "dss_token";
const USER_KEY = "dss_user";

const tabLogin = document.getElementById("tabLogin");
const tabSignup = document.getElementById("tabSignup");
const loginForm = document.getElementById("loginForm");
const signupForm = document.getElementById("signupForm");
const authAlert = document.getElementById("authAlert");

const loginSubmitBtn = document.getElementById("loginSubmitBtn");
const signupSubmitBtn = document.getElementById("signupSubmitBtn");

function showAlert(message, type = "error") {
    if (!authAlert) return;
    authAlert.textContent = message;
    authAlert.className = `auth-alert ${type}`;
}

function clearAlert() {
    if (!authAlert) return;
    authAlert.textContent = "";
    authAlert.className = "auth-alert";
}

function switchTab(mode) {
    clearAlert();
    if (mode === "login") {
        tabLogin.classList.add("active");
        tabLogin.setAttribute("aria-selected", "true");
        tabSignup.classList.remove("active");
        tabSignup.setAttribute("aria-selected", "false");
        loginForm.classList.remove("hidden");
        signupForm.classList.add("hidden");
    } else {
        tabSignup.classList.add("active");
        tabSignup.setAttribute("aria-selected", "true");
        tabLogin.classList.remove("active");
        tabLogin.setAttribute("aria-selected", "false");
        signupForm.classList.remove("hidden");
        loginForm.classList.add("hidden");
    }
}

if (tabLogin && tabSignup) {
    tabLogin.addEventListener("click", () => switchTab("login"));
    tabSignup.addEventListener("click", () => switchTab("signup"));
}

function getPostLoginRedirect() {
    const params = new URLSearchParams(window.location.search);
    const returnTo = params.get("returnTo");
    if (returnTo) {
        try {
            const decoded = decodeURIComponent(returnTo).trim();
            // Sanitize redirect target: must not be root / landing / auth pages
            if (
                decoded &&
                decoded !== "/" &&
                !decoded.includes("landing.html") &&
                !decoded.includes("auth.html") &&
                (decoded.startsWith("/") || decoded.endsWith(".html"))
            ) {
                return decoded;
            }
        } catch (e) {
            console.error("Error decoding returnTo param:", e);
        }
    }
    return "dashboard.html";
}

// Auto-switch to signup tab if URL has ?mode=signup
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get("mode") === "signup") {
    switchTab("signup");
}

if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlert();

        const email = document.getElementById("loginEmail").value.trim();
        const password = document.getElementById("loginPassword").value;

        if (!email || !password) {
            showAlert("Please enter both email and password.");
            return;
        }

        loginSubmitBtn.disabled = true;
        loginSubmitBtn.textContent = "Signing In...";

        try {
            const response = await fetch("/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.detail || "Invalid email or password.");
            }

            // Synchronously store JWT tokens and user metadata
            sessionStorage.setItem(TOKEN_KEY, data.access_token);
            sessionStorage.setItem("dss_jwt", data.access_token);
            sessionStorage.setItem(USER_KEY, JSON.stringify(data.user));

            const target = getPostLoginRedirect();
            console.log(`[Auth] Login successful. Redirecting to: ${target}`);
            showAlert("Signed in successfully! Redirecting...", "success");

            setTimeout(() => {
                window.location.href = target;
            }, 250);
        } catch (err) {
            showAlert(err.message || "Failed to sign in. Please check your credentials.");
        } finally {
            loginSubmitBtn.disabled = false;
            loginSubmitBtn.textContent = "Sign In to DSS";
        }
    });
}

if (signupForm) {
    signupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlert();

        const email = document.getElementById("signupEmail").value.trim();
        const password = document.getElementById("signupPassword").value;
        const role = document.getElementById("signupRole").value;

        if (!email || !password) {
            showAlert("Please fill in all required fields.");
            return;
        }

        if (password.length < 6) {
            showAlert("Password must be at least 6 characters.");
            return;
        }

        signupSubmitBtn.disabled = true;
        signupSubmitBtn.textContent = "Creating Account...";

        try {
            const response = await fetch("/auth/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password, role }),
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.detail || "Registration failed.");
            }

            // Synchronously store JWT tokens and user metadata
            sessionStorage.setItem(TOKEN_KEY, data.access_token);
            sessionStorage.setItem("dss_jwt", data.access_token);
            sessionStorage.setItem(USER_KEY, JSON.stringify(data.user));

            const target = getPostLoginRedirect();
            console.log(`[Auth] Registration successful. Redirecting to: ${target}`);
            showAlert("Account created successfully! Redirecting...", "success");

            setTimeout(() => {
                window.location.href = target;
            }, 250);
        } catch (err) {
            showAlert(err.message || "Registration failed. Please try again.");
        } finally {
            signupSubmitBtn.disabled = false;
            signupSubmitBtn.textContent = "Create Account";
        }
    });
}
