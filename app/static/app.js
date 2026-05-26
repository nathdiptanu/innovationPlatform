const previewTags = new Set(["A", "ABBR", "B", "BLOCKQUOTE", "BR", "CODE", "EM", "H2", "H3", "I", "LI", "OL", "P", "PRE", "STRONG", "TABLE", "TBODY", "TD", "TH", "THEAD", "TR", "UL"]);
const previewAttributes = { A: new Set(["href", "title", "target"]), TD: new Set(["colspan"]), TH: new Set(["colspan"]) };

function sanitizePreviewHtml(value) {
    const template = document.createElement("template");
    template.innerHTML = value;
    template.content.querySelectorAll("*").forEach((node) => {
        if (!previewTags.has(node.tagName)) {
            node.replaceWith(...node.childNodes);
            return;
        }
        [...node.attributes].forEach((attribute) => {
            const allowed = previewAttributes[node.tagName];
            if (!allowed || !allowed.has(attribute.name)) node.removeAttribute(attribute.name);
        });
        if (node.tagName === "A" && node.href && !["http:", "https:", "mailto:"].includes(new URL(node.href, location.href).protocol)) {
            node.removeAttribute("href");
        }
    });
    return template.innerHTML;
}

function renderPreview() {
    const input = document.querySelector("[data-content-input]");
    const preview = document.querySelector("[data-content-preview]");
    const format = document.querySelector("input[name='content_format']:checked");
    if (!input || !preview || !format) return;
    if (format.value === "html") {
        preview.innerHTML = sanitizePreviewHtml(input.value);
    } else {
        preview.textContent = input.value;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    if (window.lucide) window.lucide.createIcons();
    document.querySelectorAll(".flash.success").forEach((flash) => {
        const popup = document.createElement("div");
        popup.className = "success-popup";
        popup.textContent = flash.textContent.trim();
        popup.setAttribute("role", "status");
        document.body.appendChild(popup);
        window.setTimeout(() => popup.remove(), 5200);
    });
    document.querySelectorAll("form[data-confirm-twice], form:has([data-confirm-twice])").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const submitter = event.submitter;
            if (!form.matches("[data-confirm-twice]") && !submitter?.matches("[data-confirm-twice]")) return;
            const needsSelection = form.dataset.requiresSelection === "true" || submitter?.dataset.requiresSelection === "true";
            const selected = form.querySelectorAll("input[type='checkbox']:checked").length;
            if (needsSelection && !selected) {
                event.preventDefault();
                window.alert("Select at least one assigned jury lead or member to remove.");
                return;
            }
            const message = form.dataset.confirmTwice || submitter?.dataset.confirmTwice || "Remove selected assignment?";
            if (!window.confirm(message) || !window.confirm("Final confirmation: this will remove the selected jury assignment(s). Continue?")) {
                event.preventDefault();
            }
        });
    });
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = button.parentElement?.querySelector("input");
            if (!input) return;
            const showing = input.type === "text";
            input.type = showing ? "password" : "text";
            button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
            button.innerHTML = showing ? '<i data-lucide="eye"></i>' : '<i data-lucide="eye-off"></i>';
            if (window.lucide) window.lucide.createIcons();
        });
    });
    document.querySelectorAll("[data-content-input], input[name='content_format']").forEach((node) => {
        node.addEventListener("input", renderPreview);
        node.addEventListener("change", renderPreview);
    });
    renderPreview();
    const categoryGrid = document.querySelector("[data-category-limit]");
    if (categoryGrid) {
        categoryGrid.addEventListener("change", () => {
            const checked = categoryGrid.querySelectorAll("input:checked");
            categoryGrid.querySelectorAll("input:not(:checked)").forEach((input) => {
                input.disabled = checked.length >= Number(categoryGrid.dataset.categoryLimit);
            });
        });
    }
    document.querySelectorAll("[data-score-range]").forEach((range) => {
        const output = range.parentElement.querySelector("[data-score-output]");
        range.addEventListener("input", () => {
            output.value = range.value;
            output.textContent = range.value;
        });
    });
    const imageDialog = document.querySelector("[data-image-dialog]");
    const imagePreview = document.querySelector("[data-image-dialog-preview]");
    const imageTitle = document.querySelector("[data-image-dialog-title]");
    document.querySelectorAll("[data-image-preview]").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            imagePreview.src = trigger.dataset.imagePreview;
            imagePreview.alt = trigger.dataset.imageTitle || "Idea attachment";
            imageTitle.textContent = trigger.dataset.imageTitle || "Idea attachment";
            imageDialog.showModal();
        });
    });
    document.querySelector("[data-image-close]")?.addEventListener("click", () => imageDialog.close());
    imageDialog?.addEventListener("click", (event) => {
        if (event.target === imageDialog) imageDialog.close();
    });
    document.querySelectorAll("[data-countdown]").forEach((countdown) => {
        const output = countdown.querySelector("[data-countdown-value]");
        const deadline = new Date(countdown.dataset.deadline);
        let timer;
        const updateCountdown = () => {
            const remaining = deadline.getTime() - Date.now();
            if (remaining <= 0) {
                output.textContent = "Submission closed";
                window.clearInterval(timer);
                return;
            }
            const days = Math.floor(remaining / 86400000);
            const hours = Math.floor((remaining % 86400000) / 3600000);
            const minutes = Math.floor((remaining % 3600000) / 60000);
            const seconds = Math.floor((remaining % 60000) / 1000);
            output.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        };
        updateCountdown();
        timer = window.setInterval(updateCountdown, 1000);
    });
});
