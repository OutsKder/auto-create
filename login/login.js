const loginStage = document.getElementById("loginStage");
const loginCard = document.getElementById("loginCard");
const moonScene = document.getElementById("moonScene");
const loginForm = document.getElementById("loginForm");
const authModeSwitch = document.getElementById("authModeSwitch");
const emailInput = document.getElementById("emailInput");
const passwordInput = document.getElementById("passwordInput");
const codeInput = document.getElementById("codeInput");
const codeFieldWrap = document.getElementById("codeFieldWrap");
const sendCodeBtn = document.getElementById("sendCodeBtn");
const rememberInput = document.getElementById("rememberInput");
const loginSubmitBtn = document.getElementById("loginSubmitBtn");
const togglePasswordBtn = document.getElementById("togglePasswordBtn");
const loginFeedback = document.getElementById("loginFeedback");
const capsTip = document.getElementById("capsTip");
const fieldWraps = Array.from(document.querySelectorAll("[data-field-wrap]"));

const CODE_COOLDOWN_SECONDS = 60;
let authMode = "login";
let cooldownTimer = null;
let cooldownSeconds = 0;
let moonShiftTimer = null;

const loginParams = new URLSearchParams(window.location.search);
if (loginParams.get("entry") === "splash") {
  window.requestAnimationFrame(() => {
    document.body.classList.add("is-entering");
    window.setTimeout(() => {
      document.body.classList.remove("is-entering");
    }, 1200);
  });
}

if (window.AuthSession) {
  window.AuthSession.redirectIfAuthenticated("../index.html");
}

bindLoginEvents();
syncAuthModeUI();

function bindLoginEvents() {
  loginForm.addEventListener("submit", handleSubmit);
  loginForm.addEventListener("keydown", handleFormKeydown);
  if (authModeSwitch) {
    authModeSwitch.addEventListener("click", handleAuthModeChange);
  }
  if (sendCodeBtn) {
    sendCodeBtn.addEventListener("click", handleSendCode);
  }
  togglePasswordBtn.addEventListener("click", togglePasswordVisibility);
  passwordInput.addEventListener("keyup", detectCapsLock);
  passwordInput.addEventListener("keydown", detectCapsLock);
  loginStage.addEventListener("mousemove", handleCardTilt);
  loginStage.addEventListener("mouseleave", resetCardTilt);

  for (const wrap of fieldWraps) {
    const input = wrap.querySelector("input");
    if (!input) {
      continue;
    }

    input.addEventListener("focus", () => {
      wrap.classList.add("is-focused");
    });

    input.addEventListener("blur", () => {
      wrap.classList.remove("is-focused");
      syncFieldFilledState(input, wrap);
    });

    input.addEventListener("input", () => {
      syncFieldFilledState(input, wrap);
      clearFeedback();
    });
  }

  document.addEventListener("pointerdown", createRipple);
}

function handleAuthModeChange(event) {
  const button = event.target.closest("[data-mode]");
  if (!button) {
    return;
  }

  const nextMode = button.dataset.mode === "register" ? "register" : "login";
  if (nextMode === authMode) {
    return;
  }

  authMode = nextMode;
  clearFeedback();
  syncAuthModeUI();
}

function syncAuthModeUI() {
  const isRegister = authMode === "register";
  if (authModeSwitch) {
    const buttons = Array.from(authModeSwitch.querySelectorAll("[data-mode]"));
    for (const button of buttons) {
      const active = button.dataset.mode === authMode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    }
  }

  if (codeFieldWrap) {
    codeFieldWrap.classList.toggle("is-hidden", !isRegister);
  }

  if (rememberInput) {
    rememberInput.disabled = isRegister;
    rememberInput.closest("label")?.classList.toggle("is-hidden", isRegister);
  }

  loginSubmitBtn.textContent = isRegister ? "注册并进入工作台" : "登录并进入工作台";
}

async function handleSendCode() {
  clearFeedback();
  const email = emailInput.value.trim();
  if (!isValidEmail(email)) {
    setFeedback("请输入有效邮箱后再发送验证码。", "error");
    emailInput.focus();
    return;
  }

  if (!window.AuthSession || typeof window.AuthSession.issueEmailCode !== "function") {
    setFeedback("验证码服务暂不可用。", "error");
    return;
  }

  const result = await window.AuthSession.issueEmailCode(email);
  if (!result || !result.ok) {
    setFeedback((result && result.message) || "验证码发送失败，请稍后重试。", "error");
    return;
  }

  startSendCodeCooldown(CODE_COOLDOWN_SECONDS);
  setFeedback("验证码已发送到你的邮箱，请在 5 分钟内完成验证。", "success");
}

function startSendCodeCooldown(seconds) {
  cooldownSeconds = seconds;
  if (sendCodeBtn) {
    sendCodeBtn.disabled = true;
    sendCodeBtn.textContent = `${cooldownSeconds}s 后重发`;
  }

  if (cooldownTimer) {
    window.clearInterval(cooldownTimer);
  }

  cooldownTimer = window.setInterval(() => {
    cooldownSeconds -= 1;
    if (cooldownSeconds <= 0) {
      window.clearInterval(cooldownTimer);
      cooldownTimer = null;
      if (sendCodeBtn) {
        sendCodeBtn.disabled = false;
        sendCodeBtn.textContent = "发送验证码";
      }
      return;
    }

    if (sendCodeBtn) {
      sendCodeBtn.textContent = `${cooldownSeconds}s 后重发`;
    }
  }, 1000);
}

function syncFieldFilledState(input, wrap) {
  if (input.value.trim()) {
    wrap.classList.add("is-filled");
  } else {
    wrap.classList.remove("is-filled");
  }
}

function handleCardTilt(event) {
  const rect = loginCard.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const xRatio = clamp(x / rect.width, 0, 1);
  const yRatio = clamp(y / rect.height, 0, 1);

  const tiltX = (xRatio - 0.5) * 10;
  const tiltY = (yRatio - 0.5) * 10;

  loginCard.style.setProperty("--mouse-x", String((xRatio * 100).toFixed(2)));
  loginCard.style.setProperty("--mouse-y", String((yRatio * 100).toFixed(2)));
  loginCard.style.setProperty("--tilt-x", tiltX.toFixed(2));
  loginCard.style.setProperty("--tilt-y", tiltY.toFixed(2));
}

function resetCardTilt() {
  loginCard.style.setProperty("--tilt-x", "0");
  loginCard.style.setProperty("--tilt-y", "0");
}

function togglePasswordVisibility() {
  const show = passwordInput.type === "password";
  passwordInput.type = show ? "text" : "password";
  togglePasswordBtn.textContent = show ? "隐藏" : "显示";
  togglePasswordBtn.classList.toggle("is-on", show);
  togglePasswordBtn.setAttribute("aria-pressed", String(show));
  togglePasswordBtn.setAttribute("aria-label", show ? "隐藏密码" : "显示密码");

  if (loginCard) {
    loginCard.classList.toggle("is-eclipse", show);
  }

  if (moonScene) {
    moonScene.classList.add("is-shifting");
    if (moonShiftTimer) {
      window.clearTimeout(moonShiftTimer);
    }
    moonShiftTimer = window.setTimeout(() => {
      moonScene.classList.remove("is-shifting");
      moonShiftTimer = null;
    }, 860);
  }
}

function detectCapsLock(event) {
  const on = event.getModifierState && event.getModifierState("CapsLock");
  if (on) {
    capsTip.textContent = "你已开启大写锁定，注意密码大小写。";
    capsTip.classList.add("visible");
  } else {
    capsTip.textContent = "";
    capsTip.classList.remove("visible");
  }
}

function handleFormKeydown(event) {
  if (event.key !== "Enter") {
    return;
  }

  if (event.target && event.target.type === "button") {
    return;
  }

  clearFeedback();
}

async function handleSubmit(event) {
  event.preventDefault();
  clearFeedback();

  const email = emailInput.value.trim();
  const password = passwordInput.value;
  const remember = rememberInput.checked;
  const code = codeInput ? codeInput.value.trim() : "";

  if (!isValidEmail(email)) {
    setFeedback("请输入有效邮箱地址。", "error");
    emailInput.focus();
    return;
  }

  if (password.length < 6) {
    setFeedback("密码至少 6 位。", "error");
    passwordInput.focus();
    return;
  }

  if (authMode === "register" && !/^\d{6}$/.test(code)) {
    setFeedback("请输入 6 位数字验证码。", "error");
    codeInput?.focus();
    return;
  }

  setSubmitting(true);
  setFeedback(authMode === "register" ? "正在校验验证码并创建账号..." : "正在校验账号凭证...", "success");

  window.setTimeout(async () => {
    if (!window.AuthSession) {
      setSubmitting(false);
      setFeedback("认证服务不可用，请刷新重试。", "error");
      return;
    }

    if (authMode === "register") {
      const registerResult = await window.AuthSession.registerWithEmailCode({ email, password, code });
      if (!registerResult || !registerResult.ok) {
        setSubmitting(false);
        setFeedback((registerResult && registerResult.message) || "注册失败，请稍后重试。", "error");
        return;
      }

      await window.AuthSession.createSession(registerResult.user, { remember: false });
      setFeedback("注册成功，正在进入织界工作台。", "success");
    } else {
      const loginResult = await window.AuthSession.loginWithPassword({ email, password });
      if (!loginResult || !loginResult.ok) {
        setSubmitting(false);
        setFeedback((loginResult && loginResult.message) || "登录失败，请检查账号信息。", "error");
        return;
      }

      await window.AuthSession.createSession(loginResult.user, { remember });
      setFeedback("登录成功，正在进入织界工作台。", "success");
    }

    window.setTimeout(() => {
      window.location.replace("../index.html");
    }, 280);
  }, 760);
}

function setSubmitting(submitting) {
  loginSubmitBtn.disabled = submitting;
  loginSubmitBtn.classList.toggle("is-loading", submitting);
  loginSubmitBtn.textContent = submitting ? "登录中..." : "登录并进入工作台";
}

function setFeedback(message, type) {
  loginFeedback.textContent = message;
  loginFeedback.classList.remove("is-error", "is-success");
  if (type === "error") {
    loginFeedback.classList.add("is-error");
  }
  if (type === "success") {
    loginFeedback.classList.add("is-success");
  }
}

function clearFeedback() {
  loginFeedback.textContent = "";
  loginFeedback.classList.remove("is-error", "is-success");
}

function createRipple(event) {
  const target = event.target.closest("button, .login-card");
  if (target) {
    const rect = target.getBoundingClientRect();
    const dot = document.createElement("span");
    dot.className = "ripple-dot";
    dot.style.left = `${event.clientX - rect.left}px`;
    dot.style.top = `${event.clientY - rect.top}px`;

    target.appendChild(dot);
    window.setTimeout(() => {
      dot.remove();
    }, 560);
    return;
  }

  if (!loginStage || loginCard.contains(event.target)) {
    return;
  }

  const stageRect = loginStage.getBoundingClientRect();
  const star = document.createElement("span");
  star.className = "corner-star";
  star.style.left = `${event.clientX - stageRect.left}px`;
  star.style.top = `${event.clientY - stageRect.top}px`;

  loginStage.appendChild(star);
  window.setTimeout(() => {
    star.remove();
  }, 760);
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
