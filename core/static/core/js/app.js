document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-password-confirmation]').forEach((form) => {
    const password = form.querySelector('input[name="password"]');
    const confirmation = form.querySelector('input[name="password_confirm"]');

    if (!password || !confirmation) {
      return;
    }

    const checkPasswords = () => {
      const mismatch = password.value !== confirmation.value;
      confirmation.setCustomValidity(mismatch ? 'Passwords do not match.' : '');
    };

    password.addEventListener('input', checkPasswords);
    confirmation.addEventListener('input', checkPasswords);
    checkPasswords();
  });

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (
      form instanceof HTMLFormElement
      && form.dataset.confirm
      && !window.confirm(form.dataset.confirm)
    ) {
      event.preventDefault();
    }
  });

  document.addEventListener('click', (event) => {
    const closeButton = event.target.closest('[data-bs-dismiss="alert"]');
    if (closeButton) {
      closeButton.closest('.alert')?.remove();
    }
  });
});
