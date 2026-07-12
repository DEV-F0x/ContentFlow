function cfCopy(btn, sourceId) {
  const value = document.getElementById(sourceId).value;
  navigator.clipboard.writeText(value).then(() => {
    const original = btn.textContent;
    btn.textContent = "Copied";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = original;
      btn.classList.remove("copied");
    }, 1200);
  });
}

function cfPreviewFile(input, previewId, nameId) {
  const file = input.files && input.files[0];
  const nameEl = document.getElementById(nameId);
  if (nameEl) nameEl.textContent = file ? file.name : "No file chosen";

  const previewEl = document.getElementById(previewId);
  if (!previewEl) return;
  if (file && file.type.startsWith("image/")) {
    previewEl.src = URL.createObjectURL(file);
    previewEl.hidden = false;
  } else {
    previewEl.hidden = true;
  }
}

function populateEditModal(btn) {
  document.getElementById("edit-form").action = btn.dataset.editAction;
  document.getElementById("editModalLabel").textContent = "Edit " + btn.dataset.editName;
  document.getElementById("edit-name").value = btn.dataset.editName;
  document.getElementById("edit-file").value = "";
  document.getElementById("edit-file-name").textContent = "Keep current file";
  document.getElementById("edit-file-preview").hidden = true;
  document.getElementById("edit-current-size").textContent = btn.dataset.editSize + " KB";

  const thumb = document.getElementById("edit-current-thumb");
  const ext = document.getElementById("edit-current-ext");
  if (btn.dataset.editImage === "true") {
    thumb.src = btn.dataset.editUrl;
    thumb.hidden = false;
    ext.hidden = true;
  } else {
    thumb.hidden = true;
    const parts = btn.dataset.editName.split(".");
    ext.textContent = "." + (parts.length > 1 ? parts.pop() : "?");
    ext.hidden = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".select-on-click").forEach((el) => {
    el.addEventListener("click", () => el.select());
  });

  document.querySelectorAll("[data-copy-target]").forEach((btn) => {
    btn.addEventListener("click", () => cfCopy(btn, btn.dataset.copyTarget));
  });

  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-preview-target]").forEach((input) => {
    input.addEventListener("change", () => {
      cfPreviewFile(input, input.dataset.previewTarget, input.dataset.nameTarget);
    });
  });

  const editModalEl = document.getElementById("editModal");
  if (editModalEl) {
    editModalEl.addEventListener("show.bs.modal", (event) => {
      if (event.relatedTarget) populateEditModal(event.relatedTarget);
    });
  }

  const params = new URLSearchParams(window.location.search);

  if (params.get("upload") === "1" && document.getElementById("uploadModal")) {
    new bootstrap.Modal(document.getElementById("uploadModal")).show();
  }

  const editId = params.get("edit");
  if (editId) {
    const trigger = document.querySelector('[data-edit-id="' + editId + '"]');
    if (trigger) {
      populateEditModal(trigger);
      new bootstrap.Modal(document.getElementById("editModal")).show();
    }
  }

  if (params.has("upload") || params.has("edit")) {
    const url = new URL(window.location);
    url.searchParams.delete("upload");
    url.searchParams.delete("edit");
    window.history.replaceState({}, "", url);
  }
});
