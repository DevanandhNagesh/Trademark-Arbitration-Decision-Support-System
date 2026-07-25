// app.js
import { initFormHandling, resetAll } from "./form-handling.js";
import { initLawyerFinder } from "./lawyer-finder.js";
import { setTimelineInitial } from "./results-display.js";

document.addEventListener("DOMContentLoaded", () => {
    setTimelineInitial();
    initFormHandling();
    initLawyerFinder();

    const newAnalysisBtn = document.getElementById("newAnalysisBtn");
    newAnalysisBtn.addEventListener("click", () => {
        resetAll();
    });
});
