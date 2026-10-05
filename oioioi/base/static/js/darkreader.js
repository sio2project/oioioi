import { enable, disable } from 'darkreader';

const darkModeConfig = {
  fixes: {
    css: '.texmath img { filter: invert(1) brightness(0.8) !important; }'
  }
};

if (localStorage.getItem("dark-mode") === "enabled") {
  enable({}, darkModeConfig.fixes);
}

document.addEventListener("DOMContentLoaded", function () {
  const toggleButton = document.getElementById("dark-mode-toggle");
  toggleButton.addEventListener("click", function () {
      if (localStorage.getItem("dark-mode") === "enabled") {
          disable();
          localStorage.setItem("dark-mode", "disabled");
      } else {
          enable({}, darkModeConfig.fixes);
          localStorage.setItem("dark-mode", "enabled");
      }
  });
});