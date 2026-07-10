(function () {
  var warningMessage = "Progress not saved. Are you sure you want to exit?";
  var dirtyForms = [];
  var watchedForms = document.querySelectorAll("[data-unsaved-warning]");

  function isDirty() {
    return dirtyForms.length > 0;
  }

  function markDirty(form) {
    if (dirtyForms.indexOf(form) === -1) {
      dirtyForms.push(form);
    }
  }

  function clearDirty(form) {
    if (!form) {
      dirtyForms = [];
      return;
    }

    dirtyForms = dirtyForms.filter(function (dirtyForm) {
      return dirtyForm !== form;
    });
  }

  function isEditableField(field) {
    return !field.disabled && !field.readOnly;
  }

  function setEditableListMode(form, isEditing) {
    var editableFields = form.querySelectorAll("[data-editable-field]");
    var readonlyMirrors = form.querySelectorAll("[data-readonly-mirror]");
    var saveButton = form.querySelector("[data-save-list-button]");
    var editButton = form.querySelector("[data-edit-list-button]");
    var editBanner = form.querySelector("[data-edit-mode-banner]");

    editableFields.forEach(function (field) {
      if (isEditing) {
        field.dataset.originalValue = field.value;
      } else if (field.dataset.originalValue !== undefined) {
        field.value = field.dataset.originalValue;
        delete field.dataset.originalValue;
      }

      field.disabled = !isEditing && field.tagName === "SELECT";
      field.readOnly = !isEditing && field.tagName !== "SELECT";
    });

    readonlyMirrors.forEach(function (field) {
      field.disabled = isEditing;
    });

    if (saveButton) {
      saveButton.hidden = !isEditing;
      saveButton.disabled = !isEditing;
      saveButton.classList.toggle("disabled-button", !isEditing);
    }

    if (editButton) {
      editButton.textContent = isEditing ? "Cancel Edit" : "Edit";
    }

    if (editBanner) {
      editBanner.hidden = !isEditing;
    }
  }

  watchedForms.forEach(function (form) {
    form.addEventListener("input", function (event) {
      if (event.target.matches("input, select, textarea") && isEditableField(event.target)) {
        markDirty(form);
      }
    });

    form.addEventListener("change", function (event) {
      if (event.target.matches("input, select, textarea") && isEditableField(event.target)) {
        markDirty(form);
      }
    });

    form.addEventListener("submit", function () {
      clearDirty(form);
    });
  });

  window.addEventListener("beforeunload", function (event) {
    if (window.__timesheetSkipUnsavedWarning) {
      return;
    }
    try {
      if (window.sessionStorage.getItem("timesheet-skip-unsaved-warning-once") === "true") {
        window.sessionStorage.removeItem("timesheet-skip-unsaved-warning-once");
        return;
      }
    } catch (error) {
      // Ignore storage access errors and fall back to the normal dirty-form warning.
    }

    if (!isDirty()) {
      return;
    }

    event.preventDefault();
    event.returnValue = warningMessage;
    return warningMessage;
  });

  document.addEventListener("click", function (event) {
    var editButton = event.target.closest("[data-edit-list-button]");
    var deleteButton = event.target.closest("[data-confirm-delete]");
    var link = event.target.closest("a[href]");

    if (editButton) {
      var editableList = editButton.closest("[data-editable-list]");
      var editBanner = editableList.querySelector("[data-edit-mode-banner]");
      var isEditing = editBanner && !editBanner.hidden;

      if (isEditing && dirtyForms.indexOf(editableList) !== -1 && !window.confirm(warningMessage)) {
        event.preventDefault();
        return;
      }

      clearDirty(editableList);
      setEditableListMode(editableList, !isEditing);
      return;
    }

    if (deleteButton && !window.confirm("Are you sure you want to delete this?")) {
      event.preventDefault();
      return;
    }

    if (!link || link.target === "_blank" || !isDirty()) {
      return;
    }

    if (!window.confirm(warningMessage)) {
      event.preventDefault();
      return;
    }

    clearDirty();
  });
})();
