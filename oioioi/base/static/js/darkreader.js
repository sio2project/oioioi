import { enable, disable } from 'darkreader';

if (localStorage.getItem("dark-mode") === "enabled") {
  enable();
}

document.addEventListener("DOMContentLoaded", function () {
  const toggleButton = document.getElementById("dark-mode-toggle");
  toggleButton.addEventListener("click", function () {
      if (localStorage.getItem("dark-mode") === "enabled") {
          disable();
          localStorage.setItem("dark-mode", "disabled");
      } else {
          enable();
          localStorage.setItem("dark-mode", "enabled");
      }
  });
});