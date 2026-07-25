// results-display.js

const resultsCard = document.getElementById("resultsCard");
const formCard = document.getElementById("formCard");
const statusBadge = document.getElementById("statusBadge");
const landmarkPills = document.getElementById("landmarkPills");
const lawForCount = document.getElementById("lawForCount");
const lawAgainstCount = document.getElementById("lawAgainstCount");
const optionsCount = document.getElementById("optionsCount");
const overallPosition = document.getElementById("overallPosition");
const downloadBtn = document.getElementById("downloadBtn");
const forClaimantList = document.getElementById("forClaimantList");
const againstClaimantList = document.getElementById("againstClaimantList");
const optionsList = document.getElementById("optionsList");

const steps = Array.from(document.querySelectorAll(".step"));
let summaryBar = null;

export function setTimelineInitial() {
    steps.forEach((step, idx) => {
        step.className = "step pending";
        step.querySelector(".node").textContent = idx + 1;
        step.querySelector(".step-label").textContent = step.getAttribute("data-label");
        const sub = step.querySelector(".step-sublabel");
        if (sub) {
            sub.remove();
        }
        step.style.display = "grid";
    });
    steps[0].classList.add("active");
}

export function setTimelineLoading() {
    steps.forEach((step, idx) => {
        step.className = "step pending";
        step.querySelector(".node").textContent = idx + 1;
        step.querySelector(".step-label").textContent = step.getAttribute("data-label");
        const sub = step.querySelector(".step-sublabel");
        if (sub) {
            sub.remove();
        }
        step.style.display = "grid";
    });
    steps[0].classList.add("completed");
    steps[0].querySelector(".node").textContent = "✓";
    steps[1].classList.add("active");
}

export function setTimelineResult(arbitrability) {
    if (arbitrability === "ARBITRABLE") {
        steps.forEach((step, idx) => {
            step.className = "step pending";
            step.querySelector(".node").textContent = idx + 1;
            step.querySelector(".step-label").textContent = step.getAttribute("data-label");
            const sub = step.querySelector(".step-sublabel");
            if (sub) {
                sub.remove();
            }
            step.style.display = "grid";
        });
        steps[0].classList.add("completed");
        steps[0].querySelector(".node").textContent = "✓";
        steps[1].classList.add("completed");
        steps[1].querySelector(".node").textContent = "✓";
        steps[2].classList.add("active");
    } else {
        steps.forEach((step, idx) => {
            step.className = "step pending";
            step.querySelector(".node").textContent = idx + 1;
            step.querySelector(".step-label").textContent = step.getAttribute("data-label");
            const sub = step.querySelector(".step-sublabel");
            if (sub) {
                sub.remove();
            }
            step.style.display = "grid";
        });
        steps[0].classList.add("completed");
        steps[0].querySelector(".node").textContent = "✓";
        steps[1].classList.add("completed");
        steps[1].querySelector(".node").textContent = "✓";

        const step3 = steps[2];
        step3.classList.add("active");
        step3.querySelector(".node").textContent = "3";
        step3.querySelector(".step-label").textContent = "Court Referral";
        const sublabel = document.createElement("div");
        sublabel.className = "step-sublabel";
        sublabel.textContent = "Referred to Commercial Court";
        sublabel.style.fontSize = "11px";
        sublabel.style.color = "var(--text-secondary)";
        step3.querySelector(".step-label").appendChild(sublabel);

        steps.slice(3).forEach((step) => {
            step.style.display = "none";
        });
    }
}

function updatePreview(listEl, items) {
    listEl.innerHTML = "";
    if (!items || items.length === 0) {
        const li = document.createElement("li");
        li.textContent = "No data available";
        listEl.appendChild(li);
        return;
    }
    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        listEl.appendChild(li);
    });
}

export function buildSummaryBar(expandCallback, resetCallback) {
    if (summaryBar) {
        summaryBar.remove();
    }
    const partyA = document.getElementById("partyA").value || "Party A";
    const partyB = document.getElementById("partyB").value || "Party B";
    const trademark = document.getElementById("trademarkName").value || "Trademark";
    const disputeType = document.getElementById("disputeType").value || "Dispute";

    summaryBar = document.createElement("div");
    summaryBar.id = "form-summary-bar";
    summaryBar.innerHTML = `
        <span class="summary-text">${partyA} v ${partyB} — ${trademark} — ${disputeType}</span>
        <div class="summary-actions">
            <button type="button" id="expandFormBtn">Edit ↑</button>
            <button type="button" id="resetAllBtn">New Analysis</button>
        </div>
    `;
    resultsCard.parentElement.insertBefore(summaryBar, resultsCard);

    document.getElementById("expandFormBtn").addEventListener("click", expandCallback);
    document.getElementById("resetAllBtn").addEventListener("click", resetCallback);
}

export function removeSummaryBar() {
    if (summaryBar) {
        summaryBar.style.display = "none";
    }
}

export function hideResultsCard() {
    resultsCard.classList.remove("active");
}

export function showResultsCard() {
    resultsCard.classList.add("active");
}

export function displayResults(data, expandCallback, resetCallback) {
    statusBadge.textContent = data.arbitrability;
    statusBadge.className = "status-badge";
    const arbitrabilityStatus = data.arbitrability;
    if (arbitrabilityStatus === "ARBITRABLE") {
        statusBadge.classList.add("arbitrable");
    } else {
        statusBadge.classList.add("not-arbitrable");
    }

    const warningBanner = document.getElementById("narrativeWarningBanner");
    const warningMessage = document.getElementById("narrativeWarningMessage");
    if (data.narrative_warning && data.narrative_warning.has_disagreement) {
        warningMessage.textContent = data.narrative_warning.message;
        warningBanner.style.display = "block";
    } else {
        warningBanner.style.display = "none";
    }

    const fallbackBadge = document.getElementById("fallbackWarningBadge");
    const liveBadge = document.getElementById("liveAnalysisBadge");
    if (data.generation_method === "fallback") {
        fallbackBadge.style.display = "inline-flex";
        liveBadge.style.display = "none";
    } else {
        fallbackBadge.style.display = "none";
        liveBadge.style.display = "inline-flex";
    }

    document.getElementById("errorCard").style.display = "none";

    // ── Lawyer finder context message logic ────────────────
    var lawyerMsg = document.getElementById('lawyer-context-message');
    if (arbitrabilityStatus === 'NOT ARBITRABLE') {
        lawyerMsg.textContent = 'You may need a lawyer for civil court proceedings.';
        lawyerMsg.className = 'lawyer-context-message civil';
    } else {
        lawyerMsg.textContent = 'You may consult a lawyer for arbitration representation.';
        lawyerMsg.className = 'lawyer-context-message arbitration';
    }

    document.getElementById('lawyer-finder-section').style.display = 'block';

    // Reset lawyer finder for this new analysis
    document.getElementById('lawyer-results-container').innerHTML = '';
    document.getElementById('lawyer-city-input').value = '';
    document.getElementById('location-error-msg').style.display = 'none';

    landmarkPills.innerHTML = "";
    (data.landmarks_retrieved || []).forEach((name) => {
        const span = document.createElement("span");
        span.className = "pill";
        span.textContent = name;
        landmarkPills.appendChild(span);
    });

    const summary = data.adversarial_summary || {};
    lawForCount.textContent = summary.law_for_claimant_count || 0;
    lawAgainstCount.textContent = summary.law_against_claimant_count || 0;
    optionsCount.textContent = summary.options_available_count || 0;
    const summaryText = summary.overall_position || "";
    const dotIndex = summaryText.indexOf(".");
    const previewText = dotIndex !== -1
        ? summaryText.substring(0, dotIndex + 1)
        : (summaryText.length > 120 ? summaryText.substring(0, 120) + "..." : summaryText);
    overallPosition.textContent = previewText;

    const preview = data.adversarial_preview || {};
    updatePreview(forClaimantList, preview.law_for_claimant || []);
    updatePreview(againstClaimantList, preview.law_against_claimant || []);
    updatePreview(optionsList, preview.options_available || []);

    downloadBtn.href = data.download_url;
    downloadBtn.setAttribute("download", data.report_filename || "dss_report.docx");

    formCard.style.display = "none";
    buildSummaryBar(expandCallback, resetCallback);
    showResultsCard();
    setTimelineResult(data.arbitrability);
}
