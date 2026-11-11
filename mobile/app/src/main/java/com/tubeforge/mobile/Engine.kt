package com.tubeforge.mobile

import android.content.Context
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLException
import com.yausername.youtubedl_android.YoutubeDLRequest

/**
 * Thin wrapper around the bundled yt-dlp + ffmpeg engine.
 *
 * The engine ships CPython, yt-dlp and ffmpeg inside the APK's native library
 * directory, so the first init unpacks them (a few seconds) and later calls are
 * instant.
 */
object Engine {
    private val lock = Any()

    @Volatile
    private var ready = false

    @Volatile
    var lastError: String? = null
        private set

    fun ensure(context: Context) {
        if (ready) return
        synchronized(lock) {
            if (ready) return
            try {
                YoutubeDL.getInstance().init(context.applicationContext)
                FFmpeg.getInstance().init(context.applicationContext)
                ready = true
                lastError = null
            } catch (e: Throwable) {
                lastError = e.message ?: e.javaClass.simpleName
                throw e
            }
        }
    }

    fun version(context: Context): String = try {
        YoutubeDL.version(context.applicationContext)?.takeIf { it.isNotBlank() } ?: "unknown"
    } catch (e: Throwable) {
        "unknown"
    }

    fun fetch(url: String, prefs: Prefs): MediaInfo {
        val request = YoutubeDLRequest(url)
        request.addOption("--no-playlist")
        request.addOption("--playlist-items", "1")
        request.addOption("--skip-download")
        request.addOption("--no-warnings")
        request.addOption("--socket-timeout", 20)
        val proxy = prefs.proxy.trim()
        if (proxy.isNotEmpty()) request.addOption("--proxy", proxy)

        val info = YoutubeDL.getInstance().getInfo(request)
        val formats = (info.formats ?: arrayListOf()).mapNotNull { f ->
            val id = f.formatId ?: return@mapNotNull null
            Fmt(
                id = id,
                ext = f.ext ?: "",
                vcodec = f.vcodec ?: "",
                acodec = f.acodec ?: "",
                height = f.height,
                abr = f.abr,
                tbr = f.tbr,
                size = if (f.fileSize > 0) f.fileSize else f.fileSizeApproximate,
                note = f.formatNote ?: "",
            )
        }

        return MediaInfo(
            url = url,
            title = info.title ?: info.fulltitle ?: url,
            uploader = info.uploader ?: "",
            duration = info.duration,
            thumbnail = info.thumbnail ?: "",
            formats = formats,
        )
    }

    fun update(context: Context): String {
        ensure(context)
        YoutubeDL.getInstance().updateYoutubeDL(context.applicationContext)
        return version(context)
    }

    fun cancel(processId: String): Boolean = runCatching {
        YoutubeDL.getInstance().destroyProcessById(processId)
    }.getOrDefault(false)

    fun friendly(message: String?): String {
        val text = (message ?: "").trim()
        val lower = text.lowercase()
        return when {
            text.isEmpty() -> "Download failed. Try again."
            lower.contains("sign in to confirm") || lower.contains("bot") ->
                "This video needs a signed-in account. Try another link."
            lower.contains("video unavailable") || lower.contains("removed by the uploader") ->
                "This video is unavailable or was removed."
            lower.contains("unsupported url") || lower.contains("is not a valid url") ->
                "That link isn't supported."
            lower.contains("http error 403") || lower.contains("cloudflare") ->
                "The site blocked the request (403). Try again in a moment."
            lower.contains("http error 404") ->
                "The link could not be found (404)."
            lower.contains("private video") -> "This video is private."
            lower.contains("age") && lower.contains("restrict") ->
                "This video is age-restricted and can't be downloaded."
            lower.contains("live event") || lower.contains("is live") ->
                "Live streams can't be downloaded until they finish."
            lower.contains("timed out") || lower.contains("timeout") ->
                "The connection timed out. Check your network or proxy."
            lower.contains("unable to download video data") || lower.contains("connection") ->
                "Network error while downloading. Try again."
            lower.contains("no space") || lower.contains("enospc") ->
                "Not enough free storage for this download."
            else -> {
                val line = text.split('\n').lastOrNull { it.isNotBlank() } ?: text
                line.removePrefix("ERROR:").trim().take(180)
            }
        }
    }

    fun isEngineMissing(e: Throwable): Boolean = e is YoutubeDLException
}
