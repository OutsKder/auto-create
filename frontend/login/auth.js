(function bootstrapAuthSession() {
  const AUTH_STORAGE_KEY = "zhijie-engine-auth-v1";
  const USER_STORAGE_KEY = "zhijie-engine-users-v1";
  const VERIFY_STORAGE_KEY = "zhijie-engine-verify-codes-v1";
  const DEFAULT_TTL_MS = 8 * 60 * 60 * 1000;
  const REMEMBER_TTL_MS = 7 * 24 * 60 * 60 * 1000;
  const CODE_EXPIRE_MS = 5 * 60 * 1000;

  ensureDemoUser();

  function readSession() {
    try {
      const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) {
        return null;
      }

      const parsed = JSON.parse(raw);
      if (!parsed || !parsed.user || !parsed.expiresAt) {
        return null;
      }

      return parsed;
    } catch (error) {
      console.error("Failed to read auth session:", error);
      return null;
    }
  }

  function isAuthenticated(session) {
    const active = session || readSession();
    if (!active) {
      return false;
    }

    const isValid = Number(new Date(active.expiresAt)) > Date.now();
    if (!isValid) {
      clearSession();
    }

    return isValid;
  }

  function createSession(user, options = {}) {
    const ttl = options.remember ? REMEMBER_TTL_MS : DEFAULT_TTL_MS;
    const now = Date.now();

    const session = {
      user: {
        name: String(user && user.name ? user.name : "协作者").trim() || "协作者",
        email: String(user && user.email ? user.email : "").trim(),
      },
      issuedAt: new Date(now).toISOString(),
      expiresAt: new Date(now + ttl).toISOString(),
      remember: Boolean(options.remember),
    };

    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    return session;
  }

  function clearSession() {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  function readUsers() {
    try {
      const raw = window.localStorage.getItem(USER_STORAGE_KEY);
      if (!raw) {
        return [];
      }

      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }

      return parsed;
    } catch (error) {
      console.error("Failed to read users:", error);
      return [];
    }
  }

  function saveUsers(users) {
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(users));
  }

  function readVerifyStore() {
    try {
      const raw = window.localStorage.getItem(VERIFY_STORAGE_KEY);
      if (!raw) {
        return {};
      }

      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") {
        return {};
      }

      return parsed;
    } catch (error) {
      console.error("Failed to read verify store:", error);
      return {};
    }
  }

  function saveVerifyStore(store) {
    window.localStorage.setItem(VERIFY_STORAGE_KEY, JSON.stringify(store));
  }

  function normalizeEmail(email) {
    return String(email || "").trim().toLowerCase();
  }

  function findUserByEmail(email) {
    const users = readUsers();
    const normalizedEmail = normalizeEmail(email);
    return users.find((item) => normalizeEmail(item.email) === normalizedEmail) || null;
  }

  function ensureDemoUser() {
    const users = readUsers();
    const exists = users.some((item) => normalizeEmail(item.email) === "demo@zhijie.engine");
    if (exists) {
      return;
    }

    users.push({
      id: `user_${Date.now()}`,
      email: "demo@zhijie.engine",
      password: "zhijie123",
      createdAt: new Date().toISOString(),
      isDemo: true,
    });
    saveUsers(users);
  }

  function issueEmailCode(email) {
    const normalizedEmail = normalizeEmail(email);
    if (!normalizedEmail) {
      return { ok: false, message: "邮箱不能为空。" };
    }

    const code = String(Math.floor(100000 + Math.random() * 900000));
    const now = Date.now();
    const store = readVerifyStore();

    store[normalizedEmail] = {
      code,
      issuedAt: new Date(now).toISOString(),
      expiresAt: new Date(now + CODE_EXPIRE_MS).toISOString(),
    };

    saveVerifyStore(store);

    return {
      ok: true,
      code,
      expiresInMs: CODE_EXPIRE_MS,
    };
  }

  function registerWithEmailCode(payload) {
    const normalizedEmail = normalizeEmail(payload && payload.email);
    const password = String(payload && payload.password ? payload.password : "");
    const code = String(payload && payload.code ? payload.code : "").trim();

    if (!normalizedEmail) {
      return { ok: false, message: "邮箱不能为空。" };
    }

    if (password.length < 6) {
      return { ok: false, message: "密码至少 6 位。" };
    }

    if (!/^\d{6}$/.test(code)) {
      return { ok: false, message: "请输入 6 位数字验证码。" };
    }

    if (findUserByEmail(normalizedEmail)) {
      return { ok: false, message: "该邮箱已注册，请直接登录。" };
    }

    const store = readVerifyStore();
    const record = store[normalizedEmail];
    if (!record) {
      return { ok: false, message: "请先发送验证码。" };
    }

    const notExpired = Number(new Date(record.expiresAt)) > Date.now();
    if (!notExpired) {
      return { ok: false, message: "验证码已过期，请重新获取。" };
    }

    if (String(record.code) !== code) {
      return { ok: false, message: "验证码不正确。" };
    }

    const users = readUsers();
    const nextUser = {
      id: `user_${Date.now()}`,
      email: normalizedEmail,
      password,
      createdAt: new Date().toISOString(),
      isDemo: false,
    };

    users.push(nextUser);
    saveUsers(users);

    delete store[normalizedEmail];
    saveVerifyStore(store);

    return { ok: true, user: nextUser };
  }

  function loginWithPassword(payload) {
    const normalizedEmail = normalizeEmail(payload && payload.email);
    const password = String(payload && payload.password ? payload.password : "");

    if (!normalizedEmail) {
      return { ok: false, message: "请输入邮箱。" };
    }

    const user = findUserByEmail(normalizedEmail);
    if (!user) {
      return { ok: false, message: "该邮箱尚未注册，请先注册。" };
    }

    if (String(user.password) !== password) {
      return { ok: false, message: "邮箱或密码错误。" };
    }

    return { ok: true, user };
  }

  function requireAuth(redirectTo) {
    if (isAuthenticated()) {
      return true;
    }

    window.location.replace(redirectTo || "./login.html");
    return false;
  }

  function redirectIfAuthenticated(targetUrl) {
    if (!isAuthenticated()) {
      return false;
    }

    window.location.replace(targetUrl || "./index.html");
    return true;
  }

  function getDisplayName(session) {
    const active = session || readSession();
    if (!active || !active.user) {
      return "协作者";
    }

    return String(active.user.name || active.user.email || "协作者");
  }

  window.AuthSession = {
    readSession,
    isAuthenticated,
    createSession,
    clearSession,
    issueEmailCode,
    registerWithEmailCode,
    loginWithPassword,
    requireAuth,
    redirectIfAuthenticated,
    getDisplayName,
  };
})();
