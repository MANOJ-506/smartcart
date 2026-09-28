/**
 * SmartCart - Clean Minimal JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Mobile Nav Toggle
  const navToggle = document.getElementById('navToggle');
  const navMenu = document.getElementById('navMenu');

  if (navToggle && navMenu) {
    navToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      navMenu.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (navMenu.classList.contains('open') && !navMenu.contains(e.target) && e.target !== navToggle) {
        navMenu.classList.remove('open');
      }
    });
  }

  // Image Preview for file inputs
  const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
  imageInputs.forEach((input) => {
    input.addEventListener('change', function () {
      if (this.files && this.files[0]) {
        const previewTargetId = this.getAttribute('data-preview-target');
        if (previewTargetId) {
          const previewImg = document.getElementById(previewTargetId);
          if (previewImg) {
            const reader = new FileReader();
            reader.onload = (e) => {
              previewImg.src = e.target.result;
              previewImg.style.display = 'block';
            };
            reader.readAsDataURL(this.files[0]);
          }
        }
      }
    });
  });
});
