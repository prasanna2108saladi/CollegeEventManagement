// script.js — small client-side helpers (no framework needed)

document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss flash messages after 4 seconds
    document.querySelectorAll(".alert").forEach(function (alertEl) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
            bsAlert.close();
        }, 4000);
    });

    // Confirm before deleting an event
    document.querySelectorAll(".delete-event-form").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (!confirm("Are you sure you want to delete this event? This cannot be undone.")) {
                e.preventDefault();
            }
        });
    });

    // Live preview of uploaded event image
    const imageInput = document.getElementById("image");
    const imagePreview = document.getElementById("imagePreview");
    if (imageInput && imagePreview) {
        imageInput.addEventListener("change", function () {
            const file = imageInput.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    imagePreview.src = e.target.result;
                    imagePreview.classList.remove("d-none");
                };
                reader.readAsDataURL(file);
            }
        });
    }
});
