(function bootstrapAuthSession() {
  const AUTH_STORAGE_KEY = "zhijie-engine-auth-v1";
  const USER_STORAGE_KEY = "zhijie-engine-users-v1";
  const VERIFY_STORAGE_KEY = "zhijie-engine-verify-codes-v1";
  const DEFAULT_TTL_MS = 8 * 60 * 60 * 1000;
  const REMEMBER_TTL_MS = 7 * 24 * 60 * 60 * 1000;
  const CODE_EXPIRE_MS = 5 * 60 * 1000;
  const USING_SUPABASE = Boolean(window.ZJSupabase && window.ZJSupabase.isEnabled());
  const BACKEND_BASE_URL = String(
    (window.ZHIJIE_BACKEND_CONFIG && window.ZHIJIE_BACKEND_CONFIG.baseUrl) || ""
  ).replace(/\/$/, "");

  if (!USING_SUPABASE) {
    ensureDemoUser();
  }

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

  async function createSession(user, options = {}) {
    const ttl = options.remember ? REMEMBER_TTL_MS : DEFAULT_TTL_MS;
    const now = Date.now();
    const sessionId = `sess_${now}_${Math.random().toString(16).slice(2, 10)}`;

    const session = {
      id: sessionId,
      user: {
        name: String(user && (user.name || user.display_name) ? user.name || user.display_name : "协作者").trim() || "协作者",
        email: String(user && user.email ? user.email : "").trim(),
        userId: user && user.id ? String(user.id) : null,
      },
      issuedAt: new Date(now).toISOString(),
      expiresAt: new Date(now + ttl).toISOString(),
      remember: Boolean(options.remember),
    };

    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));

    if (isSupabaseReady() && user && user.id) {
      const refreshTokenSalt = randomSalt();
      const refreshToken = `refresh_${sessionId}`;
      const refreshTokenHash = await hashSecret(refreshToken, refreshTokenSalt);
      await getSupabaseClient().from("sessions").insert({
        user_id: user.id,
        refresh_token_hash: refreshTokenHash,
        refresh_token_salt: refreshTokenSalt,
        expires_at: new Date(now + ttl).toISOString(),
        created_at: new Date(now).toISOString(),
        last_seen_at: new Date(now).toISOString(),
        user_agent: navigator.userAgent,
      });
    }

    return session;
  }

  function clearSession() {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  function getSupabaseClient() {
    return window.ZJSupabase && typeof window.ZJSupabase.getClient === "function"
      ? window.ZJSupabase.getClient()
      : null;
  }

  function isSupabaseReady() {
    return Boolean(getSupabaseClient());
  }

  function isBackendAuthReady() {
    return Boolean(BACKEND_BASE_URL);
  }

  async function postBackend(path, payload) {
    if (!isBackendAuthReady()) {
      throw new Error("Backend auth is not configured");
    }

    const response = await fetch(`${BACKEND_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    let body = null;
    try {
      body = await response.json();
    } catch (_error) {
      body = null;
    }

    if (!response.ok) {
      const detail = body && (body.detail || body.message) ? body.detail || body.message : "请求失败";
      return { ok: false, message: detail, raw: body };
    }

    return { ok: true, data: body };
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

  function randomSalt() {
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    return Array.from(bytes)
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");
  }

  function bytesToHex(buffer) {
    return Array.from(new Uint8Array(buffer))
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");
  }

  async function hashSecret(secret, salt) {
    const payload = `${String(salt || "")}:${String(secret || "")}`;
    const encoded = new TextEncoder().encode(payload);
    const digest = await window.crypto.subtle.digest("SHA-256", encoded);
    return bytesToHex(digest);
  }

  async function createHashedCredentials(secret) {
    const salt = randomSalt();
    const hash = await hashSecret(secret, salt);
    return { salt, hash };
  }

  function normalizeEmail(email) {
    return String(email || "").trim().toLowerCase();
  }

  function findUserByEmail(email) {
    const users = readUsers();
    const normalizedEmail = normalizeEmail(email);
    return users.find((item) => normalizeEmail(item.email) === normalizedEmail) || null;
  }

  async function fetchSupabaseUserByEmail(email) {
    const client = getSupabaseClient();
    if (!client) {
      return null;
    }

    const normalizedEmail = normalizeEmail(email);
    const { data, error } = await client.from("users").select("*").eq("email", normalizedEmail).maybeSingle();
    if (error) {
      throw error;
    }

    return data || null;
  }

  async function fetchLatestVerificationRecord(email, purpose) {
    const client = getSupabaseClient();
    if (!client) {
      const store = readVerifyStore();
      return store[normalizeEmail(email)] || null;
    }

    const normalizedEmail = normalizeEmail(email);
    const { data, error } = await client
      .from("email_verification_codes")
      .select("*")
      .eq("email", normalizedEmail)
      .eq("purpose", purpose)
      .order("created_at", { ascending: false })
      .limit(1);

    if (error) {
      throw error;
    }

    return Array.isArray(data) && data.length ? data[0] : null;
  }

  async function writeVerificationRecord(email, purpose, code) {
    const client = getSupabaseClient();
    const normalizedEmail = normalizeEmail(email);
    const expiresAt = new Date(Date.now() + CODE_EXPIRE_MS).toISOString();
    const { salt, hash } = await createHashedCredentials(code);

    if (client) {
      const { data, error } = await client
        .from("email_verification_codes")
        .insert({
          email: normalizedEmail,
          purpose,
          code_hash: hash,
          code_salt: salt,
          expires_at: expiresAt,
          attempt_count: 0,
        })
        .select()
        .single();

      if (error) {
        throw error;
      }

      return data;
    }

    const store = readVerifyStore();
    store[normalizedEmail] = {
      code,
      code_hash: hash,
      code_salt: salt,
      issuedAt: new Date().toISOString(),
      expiresAt,
      purpose,
    };
    saveVerifyStore(store);
    return store[normalizedEmail];
  }

  async function markVerificationRecordUsed(email, purpose, userId) {
    const client = getSupabaseClient();
    if (client) {
      const now = new Date().toISOString();
      await client
        .from("email_verification_codes")
        .update({ used_at: now, verified_user_id: userId || null })
        .eq("email", normalizeEmail(email))
        .eq("purpose", purpose)
        .is("used_at", null);
      return;
    }

    const store = readVerifyStore();
    const record = store[normalizeEmail(email)];
    if (record) {
      record.usedAt = new Date().toISOString();
      record.verifiedUserId = userId || null;
      saveVerifyStore(store);
    }
  }

  function ensureDemoUser() {
    const users = readUsers();
    const exists = users.some((item) => normalizeEmail(item.email) === "demo@zhijie.engine");
    if (exists) {
      return;
    }

    createHashedCredentials("zhijie123").then(({ salt, hash }) => {
      users.push({
        id: `user_${Date.now()}`,
        email: "demo@zhijie.engine",
        password: "zhijie123",
        password_hash: hash,
        password_salt: salt,
        createdAt: new Date().toISOString(),
        isDemo: true,
      });
      saveUsers(users);
    });
  }

  async function issueEmailCode(email) {
    const normalizedEmail = normalizeEmail(email);
    if (!normalizedEmail) {
      return { ok: false, message: "邮箱不能为空。" };
    }

    if (isBackendAuthReady()) {
      const backendResult = await postBackend("/api/v1/auth/send-code", {
        email: normalizedEmail,
        purpose: "register",
      });
      if (!backendResult.ok) {
        return { ok: false, message: backendResult.message || "验证码发送失败，请稍后重试。" };
      }

      return {
        ok: true,
        expiresInMs: Number(backendResult.data && backendResult.data.expires_in_seconds)
          ? Number(backendResult.data.expires_in_seconds) * 1000
          : CODE_EXPIRE_MS,
        via: "backend",
      };
    }

    const code = String(Math.floor(100000 + Math.random() * 900000));
    try {
      await writeVerificationRecord(normalizedEmail, "register", code);
    } catch (error) {
      console.error("Failed to write verification code:", error);
      return { ok: false, message: "验证码发送失败，请稍后重试。" };
    }

    return {
      ok: true,
      code,
      expiresInMs: CODE_EXPIRE_MS,
    };
  }

  async function registerWithEmailCode(payload) {
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

    if (isBackendAuthReady()) {
      const backendResult = await postBackend("/api/v1/auth/register", {
        email: normalizedEmail,
        password,
        code,
      });
      if (!backendResult.ok) {
        return { ok: false, message: backendResult.message || "注册失败，请稍后重试。" };
      }

      return {
        ok: true,
        user: backendResult.data && backendResult.data.user ? backendResult.data.user : { email: normalizedEmail },
      };
    }

    const record = await fetchLatestVerificationRecord(normalizedEmail, "register");
    if (!record) {
      return { ok: false, message: "请先发送验证码。" };
    }

    const alreadyUsed = Boolean(record.used_at || record.usedAt);
    if (alreadyUsed) {
      return { ok: false, message: "该验证码已被使用，请重新获取。" };
    }

    const expiresAt = record.expires_at || record.expiresAt;
    const notExpired = Number(new Date(expiresAt)) > Date.now();
    if (!notExpired) {
      return { ok: false, message: "验证码已过期，请重新获取。" };
    }

    const expectedHash = record.code_hash || null;
    const expectedSalt = record.code_salt || null;
    const hashedCode = expectedHash && expectedSalt ? await hashSecret(code, expectedSalt) : null;
    const codeMatches = expectedHash ? hashedCode === expectedHash : String(record.code || "") === code;
    if (!codeMatches) {
      return { ok: false, message: "验证码不正确。" };
    }

    const existingUser = isSupabaseReady() ? await fetchSupabaseUserByEmail(normalizedEmail) : findUserByEmail(normalizedEmail);
    if (existingUser) {
      return { ok: false, message: "该邮箱已注册，请直接登录。" };
    }

    const { salt: passwordSalt, hash: passwordHash } = await createHashedCredentials(password);
    const displayName = normalizedEmail.split("@")[0] || "协作者";
    const nextUser = {
      email: normalizedEmail,
      display_name: displayName,
      password_hash: passwordHash,
      password_salt: passwordSalt,
      status: "active",
      role: "member",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      last_login_at: null,
    };

    try {
      if (isSupabaseReady()) {
        const client = getSupabaseClient();
        const { data, error } = await client.from("users").insert(nextUser).select().single();
        if (error) {
          throw error;
        }
        await markVerificationRecordUsed(normalizedEmail, "register", data.id);
        return { ok: true, user: data };
      }

      const users = readUsers();
      users.push({
        id: `user_${Date.now()}`,
        ...nextUser,
        password: password,
        isDemo: false,
      });
      saveUsers(users);
      await markVerificationRecordUsed(normalizedEmail, "register", users[users.length - 1].id);
      return { ok: true, user: users[users.length - 1] };
    } catch (error) {
      console.error("Failed to register:", error);
      return { ok: false, message: "注册失败，请稍后重试。" };
    }
  }

  async function loginWithPassword(payload) {
    const normalizedEmail = normalizeEmail(payload && payload.email);
    const password = String(payload && payload.password ? payload.password : "");

    if (!normalizedEmail) {
      return { ok: false, message: "请输入邮箱。" };
    }

    if (isBackendAuthReady()) {
      const backendResult = await postBackend("/api/v1/auth/login", {
        email: normalizedEmail,
        password,
      });
      if (!backendResult.ok) {
        return { ok: false, message: backendResult.message || "登录失败，请检查账号信息。" };
      }

      return {
        ok: true,
        user: backendResult.data && backendResult.data.user ? backendResult.data.user : { email: normalizedEmail },
      };
    }

    const user = isSupabaseReady() ? await fetchSupabaseUserByEmail(normalizedEmail) : findUserByEmail(normalizedEmail);
    if (!user) {
      return { ok: false, message: "该邮箱尚未注册，请先注册。" };
    }

    const plainMatch = String(user.password || "") === password;
    const hashedMatch = user.password_hash && user.password_salt ? (await hashSecret(password, user.password_salt)) === user.password_hash : false;
    if (!plainMatch && !hashedMatch) {
      return { ok: false, message: "邮箱或密码错误。" };
    }

    if (isSupabaseReady()) {
      await getSupabaseClient().from("users").update({ last_login_at: new Date().toISOString() }).eq("id", user.id);
    } else {
      const users = readUsers();
      const index = users.findIndex((item) => normalizeEmail(item.email) === normalizedEmail);
      if (index >= 0) {
        users[index].last_login_at = new Date().toISOString();
        saveUsers(users);
      }
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

    return String(active.user.name || active.user.display_name || active.user.email || "协作者");
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
