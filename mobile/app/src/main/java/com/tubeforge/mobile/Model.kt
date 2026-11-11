package com.tubeforge.mobile

import org.json.JSONArray
import org.json.JSONObject

enum class JobStatus { QUEUED, DOWNLOADING, PROCESSING, DONE, ERROR, CANCELLED }

data class Job(
    val id: String,
    val url: String,
    val kind: String,
    val fmt: String,
    val quality: String = "best",
    var title: String = "Preparing download…",
    var uploader: String = "",
    var duration: Int = 0,
    var thumbUrl: String = "",
    var status: JobStatus = JobStatus.QUEUED,
    var progress: Float = 0f,
    var speed: Long = 0,
    var eta: Int = 0,
    var downloaded: Long = 0,
    var total: Long = 0,
    var totalEstimated: Boolean = false,
    var fileName: String = "",
    var uri: String = "",
    var size: Long = 0,
    var stage: String = "Queued",
    var error: String = "",
    var created: Long = System.currentTimeMillis(),
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("url", url)
        put("kind", kind)
        put("fmt", fmt)
        put("quality", quality)
        put("title", title)
        put("uploader", uploader)
        put("duration", duration)
        put("thumbUrl", thumbUrl)
        put("status", status.name)
        put("progress", progress.toDouble())
        put("total", total)
        put("totalEstimated", totalEstimated)
        put("created", created)
    }

    companion object {
        fun fromJson(o: JSONObject): Job = Job(
            id = o.optString("id"),
            url = o.optString("url"),
            kind = o.optString("kind", "audio"),
            fmt = o.optString("fmt", "mp3"),
            quality = o.optString("quality", "best"),
            title = o.optString("title", "Preparing download…"),
            uploader = o.optString("uploader"),
            duration = o.optInt("duration"),
            thumbUrl = o.optString("thumbUrl"),
            status = runCatching { JobStatus.valueOf(o.optString("status", "QUEUED")) }
                .getOrDefault(JobStatus.QUEUED),
            progress = o.optDouble("progress", 0.0).toFloat(),
            total = o.optLong("total"),
            totalEstimated = o.optBoolean("totalEstimated"),
            created = o.optLong("created", System.currentTimeMillis()),
        )
    }
}

data class HistoryEntry(
    val id: String,
    val title: String,
    val url: String,
    val label: String,
    val size: Long,
    val uri: String,
    val fileName: String,
    val mime: String,
    val createdAt: Long = System.currentTimeMillis(),
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("title", title)
        put("url", url)
        put("label", label)
        put("size", size)
        put("uri", uri)
        put("fileName", fileName)
        put("mime", mime)
        put("createdAt", createdAt)
    }

    companion object {
        fun fromJson(o: JSONObject): HistoryEntry = HistoryEntry(
            id = o.optString("id"),
            title = o.optString("title", "Download"),
            url = o.optString("url"),
            label = o.optString("label", ""),
            size = o.optLong("size"),
            uri = o.optString("uri"),
            fileName = o.optString("fileName"),
            mime = o.optString("mime", "application/octet-stream"),
            createdAt = o.optLong("createdAt", System.currentTimeMillis()),
        )

        fun listToJson(items: List<HistoryEntry>): String {
            val arr = JSONArray()
            items.forEach { arr.put(it.toJson()) }
            return arr.toString()
        }

        fun listFromJson(raw: String?): List<HistoryEntry> {
            if (raw.isNullOrBlank()) return emptyList()
            return runCatching {
                val arr = JSONArray(raw)
                (0 until arr.length()).map { fromJson(arr.getJSONObject(it)) }
            }.getOrDefault(emptyList())
        }
    }
}

data class Fmt(
    val id: String,
    val ext: String,
    val vcodec: String,
    val acodec: String,
    val height: Int,
    val abr: Int,
    val tbr: Int,
    val size: Long,
    val note: String,
) {
    val isVideo: Boolean get() = vcodec != "none" && vcodec.isNotEmpty()
    val isAudioOnly: Boolean get() = acodec != "none" && acodec.isNotEmpty() && !isVideo
}

data class MediaInfo(
    val url: String,
    val title: String,
    val uploader: String,
    val duration: Int,
    val thumbnail: String,
    val formats: List<Fmt>,
) {
    fun audioFormats(): List<Fmt> = formats.filter { it.isAudioOnly }

    fun videoHeights(): List<Int> = formats
        .filter { it.isVideo && it.height > 0 }
        .map { it.height }
        .distinct()
        .sortedDescending()
        .filter { it <= 2160 }
}
