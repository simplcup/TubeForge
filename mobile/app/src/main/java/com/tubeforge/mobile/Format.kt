package com.tubeforge.mobile

import java.util.Locale
import kotlin.math.roundToLong

object Format {
    fun bytes(value: Long): String {
        if (value <= 0) return "-"
        var n = value.toDouble()
        for (unit in listOf("B", "KB", "MB", "GB")) {
            if (n < 1024 || unit == "GB") {
                return if (unit == "B") "${n.roundToLong()} B" else String.format(Locale.US, "%.1f %s", n, unit)
            }
            n /= 1024.0
        }
        return "-"
    }

    fun speed(bytesPerSecond: Long): String {
        if (bytesPerSecond <= 0) return ""
        var n = bytesPerSecond.toDouble()
        for (unit in listOf("B/s", "KB/s", "MB/s", "GB/s")) {
            if (n < 1024 || unit == "GB/s") {
                return if (unit == "B/s") "${n.roundToLong()} B/s" else String.format(Locale.US, "%.1f %s", n, unit)
            }
            n /= 1024.0
        }
        return ""
    }

    fun eta(seconds: Int): String {
        if (seconds <= 0) return ""
        val s = seconds % 60
        val m = (seconds / 60) % 60
        val h = seconds / 3600
        return if (h > 0) String.format(Locale.US, "%d:%02d:%02d", h, m, s)
        else String.format(Locale.US, "%02d:%02d", m, s)
    }

    fun duration(seconds: Int): String {
        if (seconds <= 0) return ""
        val s = seconds % 60
        val m = (seconds / 60) % 60
        val h = seconds / 3600
        return if (h > 0) String.format(Locale.US, "%d:%02d:%02d", h, m, s)
        else String.format(Locale.US, "%d:%02d", m, s)
    }

    fun date(millis: Long): String {
        val fmt = java.text.SimpleDateFormat("d MMM, HH:mm", Locale.getDefault())
        return fmt.format(java.util.Date(millis))
    }

    fun extensionFromName(name: String): String =
        name.substringAfterLast('.', "").lowercase(Locale.US)

    fun mimeFor(ext: String): String = when (ext.lowercase(Locale.US)) {
        "mp3" -> "audio/mpeg"
        "m4a" -> "audio/mp4"
        "opus", "ogg" -> "audio/ogg"
        "flac" -> "audio/flac"
        "wav" -> "audio/wav"
        "mp4" -> "video/mp4"
        "webm" -> "video/webm"
        "mkv" -> "video/x-matroska"
        else -> "application/octet-stream"
    }

    fun formatLabel(fmt: String, kind: String): String = when (fmt.lowercase(Locale.US)) {
        "mp3" -> "MP3 · 320 kbps"
        "m4a" -> "M4A · AAC audio"
        "opus" -> "OPUS · original quality"
        "flac" -> "FLAC · lossless"
        "wav" -> "WAV · uncompressed"
        "mp4" -> "MP4 · H.264"
        "webm" -> "WEBM · VP9"
        "mkv" -> "MKV · any codec"
        else -> fmt.uppercase(Locale.US) + if (kind == "audio") " · audio" else " · video"
    }
}
