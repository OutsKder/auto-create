const SPLASH_DURATION_MS = 3600;
const REDIRECT_DELAY_MS = 0;

const splashStage = document.getElementById("splashStage");
if (splashStage) {
  splashStage.addEventListener("click", skipSplash);
}

window.setTimeout(() => {
  navigateToLogin();
}, SPLASH_DURATION_MS + REDIRECT_DELAY_MS);

function skipSplash() {
  navigateToLogin();
}

function navigateToLogin() {
  window.location.replace("./login.html?entry=splash");
}
