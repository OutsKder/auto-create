(function bootstrapSupabaseBridge() {
  const config = window.ZHIJIE_SUPABASE_CONFIG || {};
  const hasClient = typeof window.supabase !== "undefined" && typeof window.supabase.createClient === "function";
  const enabled = Boolean(config.url && config.anonKey && hasClient);

  let client = null;
  if (enabled) {
    client = window.supabase.createClient(config.url, config.anonKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
      },
    });
  }

  function isEnabled() {
    return enabled;
  }

  function getClient() {
    return client;
  }

  async function fetchOne(tableName, filters = {}) {
    if (!client) {
      return { data: null, error: new Error("Supabase client is not configured") };
    }

    let query = client.from(tableName).select("*").limit(1);
    for (const [key, value] of Object.entries(filters)) {
      query = query.eq(key, value);
    }

    const { data, error } = await query.maybeSingle();
    return { data, error };
  }

  async function insertRow(tableName, payload) {
    if (!client) {
      return { data: null, error: new Error("Supabase client is not configured") };
    }

    return client.from(tableName).insert(payload).select().single();
  }

  async function updateRows(tableName, payload, filters = {}) {
    if (!client) {
      return { data: null, error: new Error("Supabase client is not configured") };
    }

    let query = client.from(tableName).update(payload);
    for (const [key, value] of Object.entries(filters)) {
      query = query.eq(key, value);
    }

    return query.select();
  }

  window.ZJSupabase = {
    isEnabled,
    getClient,
    fetchOne,
    insertRow,
    updateRows,
  };
})();
