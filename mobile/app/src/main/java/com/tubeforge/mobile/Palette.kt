package com.tubeforge.mobile

import android.graphics.Color
import kotlin.math.pow

data class Palette(
    val id: String,
    val name: String,
    val blurb: String,
    val bg: Int,
    val sidebar: Int,
    val card: Int,
    val card2: Int,
    val input: Int,
    val border: Int,
    val border2: Int,
    val text: Int,
    val muted: Int,
    val dim: Int,
    val accent: Int,
    val accent2: Int,
    val accent3: Int,
    val success: Int,
    val danger: Int,
    val warning: Int,
) {
    val accentSoft: Int get() = withAlpha(accent, 0.14f)
    val accentSoft2: Int get() = withAlpha(accent, 0.24f)
    val onAccent: Int get() = if (luminance(accent) > 0.42) Color.parseColor("#0B0E14") else Color.WHITE

    fun withAlpha(color: Int, fraction: Float): Int {
        val f = fraction.coerceIn(0f, 1f)
        return Color.argb((f * 255).toInt(), Color.red(color), Color.green(color), Color.blue(color))
    }
}

private fun channel(value: Int): Double {
    val s = value / 255.0
    return if (s <= 0.03928) s / 12.92 else ((s + 0.055) / 1.055).pow(2.4)
}

fun luminance(color: Int): Double =
    0.2126 * channel(Color.red(color)) +
        0.7152 * channel(Color.green(color)) +
        0.0722 * channel(Color.blue(color))

object Palettes {
    private fun p(
        id: String,
        name: String,
        blurb: String,
        values: Map<String, String>,
    ): Palette = Palette(
        id = id,
        name = name,
        blurb = blurb,
        bg = Color.parseColor(values["bg"]),
        sidebar = Color.parseColor(values["sidebar"]),
        card = Color.parseColor(values["card"]),
        card2 = Color.parseColor(values["card2"]),
        input = Color.parseColor(values["input"]),
        border = Color.parseColor(values["border"]),
        border2 = Color.parseColor(values["border2"]),
        text = Color.parseColor(values["text"]),
        muted = Color.parseColor(values["muted"]),
        dim = Color.parseColor(values["dim"]),
        accent = Color.parseColor(values["accent"]!!),
        accent2 = Color.parseColor(values["accent2"]!!),
        accent3 = Color.parseColor(values["accent3"]!!),
        success = Color.parseColor(values["success"]!!),
        danger = Color.parseColor(values["danger"]!!),
        warning = Color.parseColor(values["warning"]!!),
    )

    val all: List<Palette> = listOf(
        p(
            "midnight", "Midnight Violet", "Deep navy with violet and cyan accents.",
            mapOf(
                "bg" to "#0B0E14", "sidebar" to "#090B11", "card" to "#111621", "card2" to "#151B28",
                "input" to "#0E131D", "border" to "#202838", "border2" to "#2B3548", "text" to "#F3F6FC",
                "muted" to "#8B95AB", "dim" to "#66718A", "accent" to "#7C5CFF", "accent2" to "#22D3EE",
                "accent3" to "#A78BFA", "success" to "#34D399", "danger" to "#FB7185", "warning" to "#FBBF24",
            ),
        ),
        p(
            "aurora", "Aurora", "Arctic green and sky blue over pine black.",
            mapOf(
                "bg" to "#061210", "sidebar" to "#040D0B", "card" to "#0C1A16", "card2" to "#10211C",
                "input" to "#081511", "border" to "#1B3128", "border2" to "#274438", "text" to "#EFFBF5",
                "muted" to "#87A99A", "dim" to "#5C7A6D", "accent" to "#34D399", "accent2" to "#38BDF8",
                "accent3" to "#6EE7B7", "success" to "#34D399", "danger" to "#FB7185", "warning" to "#FBBF24",
            ),
        ),
        p(
            "sunset", "Sunset Heat", "Warm plum with orange and pink glow.",
            mapOf(
                "bg" to "#140A10", "sidebar" to "#0F060B", "card" to "#1E1017", "card2" to "#26151D",
                "input" to "#180C12", "border" to "#36202B", "border2" to "#4A2C3A", "text" to "#FFF3F0",
                "muted" to "#B99099", "dim" to "#7E616A", "accent" to "#FB923C", "accent2" to "#F472B6",
                "accent3" to "#FDBA74", "success" to "#4ADE80", "danger" to "#FB7185", "warning" to "#FBBF24",
            ),
        ),
        p(
            "ocean", "Deep Ocean", "Midnight blue with electric blue and cyan.",
            mapOf(
                "bg" to "#061019", "sidebar" to "#040C13", "card" to "#0A1926", "card2" to "#0E2031",
                "input" to "#07131F", "border" to "#16324A", "border2" to "#204560", "text" to "#EFF7FF",
                "muted" to "#86A3BC", "dim" to "#5C7A93", "accent" to "#3B82F6", "accent2" to "#22D3EE",
                "accent3" to "#7DD3FC", "success" to "#34D399", "danger" to "#FB7185", "warning" to "#FBBF24",
            ),
        ),
        p(
            "forest", "Evergreen", "Mossy black with lime and amber highlights.",
            mapOf(
                "bg" to "#0A1009", "sidebar" to "#070C06", "card" to "#101A0F", "card2" to "#152216",
                "input" to "#0C140B", "border" to "#21341F", "border2" to "#2F4A2C", "text" to "#F2FBEF",
                "muted" to "#9AAF95", "dim" to "#6A7F66", "accent" to "#84CC16", "accent2" to "#F59E0B",
                "accent3" to "#BEF264", "success" to "#4ADE80", "danger" to "#FB7185", "warning" to "#FBBF24",
            ),
        ),
        p(
            "crimson", "Crimson", "Oxblood shadows with rose and red accents.",
            mapOf(
                "bg" to "#130A0E", "sidebar" to "#0E0609", "card" to "#1D1015", "card2" to "#27151C",
                "input" to "#170B11", "border" to "#39202B", "border2" to "#4E2C3B", "text" to "#FFF1F4",
                "muted" to "#BE8F99", "dim" to "#86626C", "accent" to "#F43F5E", "accent2" to "#FB7185",
                "accent3" to "#FDA4AF", "success" to "#34D399", "danger" to "#FB7185", "warning" to "#FBBF24",
            ),
        ),
        p(
            "graphite", "Graphite (mono)", "Monochrome charcoal with silver accents.",
            mapOf(
                "bg" to "#0B0B0D", "sidebar" to "#070708", "card" to "#131316", "card2" to "#19191D",
                "input" to "#0F0F12", "border" to "#26262B", "border2" to "#35353C", "text" to "#F4F4F6",
                "muted" to "#9C9CA4", "dim" to "#6D6D75", "accent" to "#A1A1AA", "accent2" to "#D4D4D8",
                "accent3" to "#E4E4E7", "success" to "#A3B3A8", "danger" to "#C9A7A7", "warning" to "#C9C0A0",
            ),
        ),
        p(
            "sand", "Sepia (mono)", "Warm monochrome sepia with sand accents.",
            mapOf(
                "bg" to "#12100B", "sidebar" to "#0D0B07", "card" to "#1C1811", "card2" to "#241F17",
                "input" to "#16130D", "border" to "#332C1F", "border2" to "#473D2B", "text" to "#F7F1E4",
                "muted" to "#B3A58C", "dim" to "#80745E", "accent" to "#D4A373", "accent2" to "#E9C46A",
                "accent3" to "#FAEDCD", "success" to "#B7C4A0", "danger" to "#D9A3A3", "warning" to "#E0C080",
            ),
        ),
    )

    fun get(id: String?): Palette = all.firstOrNull { it.id == id } ?: all.first()
}
