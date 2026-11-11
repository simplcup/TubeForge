package com.tubeforge.mobile

import android.content.Context

class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("tubeforge", Context.MODE_PRIVATE)

    var themeId: String
        get() = sp.getString("theme", "midnight") ?: "midnight"
        set(value) = sp.edit().putString("theme", value).apply()

    var proxy: String
        get() = sp.getString("proxy", "") ?: ""
        set(value) = sp.edit().putString("proxy", value.trim()).apply()

    var embedThumb: Boolean
        get() = sp.getBoolean("embed_thumb", true)
        set(value) = sp.edit().putBoolean("embed_thumb", value).apply()

    var embedMeta: Boolean
        get() = sp.getBoolean("embed_meta", true)
        set(value) = sp.edit().putBoolean("embed_meta", value).apply()

    var lastFormat: String
        get() = sp.getString("last_format", "mp3") ?: "mp3"
        set(value) = sp.edit().putString("last_format", value).apply()

    var lastQuality: String
        get() = sp.getString("last_quality", "best") ?: "best"
        set(value) = sp.edit().putString("last_quality", value).apply()
}
