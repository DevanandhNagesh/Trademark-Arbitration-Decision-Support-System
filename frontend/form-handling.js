// form-handling.js
import {
    displayResults,
    setTimelineInitial,
    setTimelineLoading,
    removeSummaryBar,
    hideResultsCard
} from "./results-display.js";

const form = document.getElementById("disputeForm");
const submitBtn = document.getElementById("submitBtn");
const loadingOverlay = document.getElementById("loadingOverlay");
const loadingText = document.getElementById("loadingText");
const formCard = document.getElementById("formCard");
const disputeDesc = document.getElementById("disputeDesc");
const charCount = document.getElementById("charCount");
const arbClauseGroup = document.getElementById("arbClauseGroup");

const rightSourceInput = document.getElementById("rightSourceInput");
const hasContractInput = document.getElementById("hasContractInput");
const arbClauseInput = document.getElementById("arbClauseInput");
const affectsThirdInput = document.getElementById("affectsThirdInput");

const loadingMessages = [
    "Reviewing dispute details and party submissions...",
    "Determining arbitrability under Indian law...",
    "Retrieving relevant landmark cases...",
    "Analysing applicable statutory provisions...",
    "Conducting adversarial legal analysis...",
    "Preparing structured decision framework...",
    "Generating DSS report document..."
];

let loadingInterval = null;
let loadingIndex = 0;

function startLoadingMessages() {
    loadingIndex = 0;
    loadingText.textContent = loadingMessages[0];
    loadingInterval = setInterval(() => {
        loadingIndex = (loadingIndex + 1) % loadingMessages.length;
        loadingText.textContent = loadingMessages[loadingIndex];
    }, 2000);
}

function stopLoadingMessages() {
    if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
    }
}

function setToggleValue(group, input) {
    group.querySelectorAll(".toggle-btn").forEach((btn) => {
        btn.classList.remove("active");
    });
    group.addEventListener("click", (event) => {
        const button = event.target.closest(".toggle-btn");
        if (!button) return;
        group.querySelectorAll(".toggle-btn").forEach((btn) => btn.classList.remove("active"));
        button.classList.add("active");
        input.value = button.getAttribute("data-value");

        if (input === hasContractInput) {
            if (input.value === "true") {
                arbClauseGroup.classList.add("active");
            } else {
                arbClauseGroup.classList.remove("active");
                arbClauseInput.value = "false";
                const arbButtons = arbClauseGroup.querySelectorAll(".toggle-btn");
                arbButtons.forEach((btn) => btn.classList.remove("active"));
                arbButtons[1].classList.add("active");
            }
        }
    });
}

export function expandForm() {
    removeSummaryBar();
    document.getElementById("errorCard").style.display = "none";
    formCard.style.display = "block";
    formCard.scrollIntoView({ behavior: "smooth" });
}

export function resetAll() {
    removeSummaryBar();
    document.getElementById("errorCard").style.display = "none";
    const warningBanner = document.getElementById("narrativeWarningBanner");
    if (warningBanner) {
        warningBanner.style.display = "none";
    }
    const fallbackBadge = document.getElementById("fallbackWarningBadge");
    if (fallbackBadge) {
        fallbackBadge.style.display = "none";
    }
    const liveBadge = document.getElementById("liveAnalysisBadge");
    if (liveBadge) {
        liveBadge.style.display = "none";
    }
    hideResultsCard();
    form.reset();
    rightSourceInput.value = "";
    hasContractInput.value = "";
    arbClauseInput.value = "";
    affectsThirdInput.value = "";
    document.querySelectorAll(".toggle-btn").forEach((btn) => btn.classList.remove("active"));
    arbClauseGroup.classList.remove("active");
    setTimelineInitial();
    charCount.textContent = "0 characters";
    charCount.classList.remove("low", "mid", "good");
    formCard.style.display = "block";
    formCard.scrollIntoView({ behavior: "smooth" });
}

export function initFormHandling() {
    setToggleValue(document.querySelector('[data-toggle="right_source"]'), rightSourceInput);
    setToggleValue(document.querySelector('[data-toggle="has_contract"]'), hasContractInput);
    setToggleValue(document.querySelector('[data-toggle="has_arbitration_clause"]'), arbClauseInput);
    setToggleValue(document.querySelector('[data-toggle="affects_third_parties"]'), affectsThirdInput);

    disputeDesc.addEventListener("input", () => {
        const len = disputeDesc.value.length;
        charCount.textContent = len + " characters";
        charCount.classList.remove("low", "mid", "good");
        if (len < 100) charCount.classList.add("low");
        else if (len < 300) charCount.classList.add("mid");
        else charCount.classList.add("good");
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (disputeDesc.value.length < 100) {
            alert("Dispute description must be at least 100 characters.");
            return;
        }

        if (!rightSourceInput.value || !hasContractInput.value || !affectsThirdInput.value) {
            alert("Please complete all toggle selections.");
            return;
        }

        if (hasContractInput.value === "true" && !arbClauseInput.value) {
            alert("Please select arbitration clause status.");
            return;
        }

        submitBtn.disabled = true;
        submitBtn.classList.add("loading");
        submitBtn.innerHTML = "Analysing Dispute...";
        loadingOverlay.classList.add("active");
        startLoadingMessages();
        setTimelineLoading();

        try {
            const formData = new FormData(form);
            if (!formData.get("has_arbitration_clause")) {
                formData.set("has_arbitration_clause", "false");
            }

            const response = await fetch("/analyze", {
                method: "POST",
                body: formData
            });
            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.detail || "Analysis failed");
            }

            loadingOverlay.classList.remove("active");
            stopLoadingMessages();

            displayResults(data, expandForm, resetAll);
        } catch (err) {
            loadingOverlay.classList.remove("active");
            stopLoadingMessages();
            setTimelineInitial();

            const message = err.message || "Unexpected error occurred";
            const category = getErrorCategory(message);

            document.getElementById("errorCategory").textContent = category;
            document.getElementById("errorMessage").textContent = message;

            formCard.style.display = "none";
            hideResultsCard();
            document.getElementById("errorCard").style.display = "block";
            document.getElementById("errorCard").scrollIntoView({ behavior: "smooth" });
        } finally {
            submitBtn.disabled = false;
            submitBtn.classList.remove("loading");
            submitBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 20h18" /><path d="M6 20V8l6-4 6 4v12" /><path d="M9 20v-6h6v6" /></svg>Generate DSS Report';
        }
    });

    document.getElementById("retryBtn").addEventListener("click", () => {
        document.getElementById("errorCard").style.display = "none";
        formCard.style.display = "block";
        form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
}

function getErrorCategory(message) {
    const msg = (message || "").toLowerCase();
    if (msg.includes("gemini") || msg.includes("groq") || msg.includes("lm_studio") || msg.includes("lm studio") || msg.includes("llm") || msg.includes("rate limit") || msg.includes("quota") || msg.includes("api key") || msg.includes("auth")) {
        return "LLM services unavailable";
    }
    if (msg.includes("invalid") || msg.includes("missing") || msg.includes("required") || msg.includes("validation") || msg.includes("value")) {
        return "Invalid input";
    }
    return "Server processing error";
}
