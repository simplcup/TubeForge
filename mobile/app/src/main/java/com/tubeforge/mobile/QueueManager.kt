package com.tubeforge.mobile

import android.content.Context
import android.os.SystemClock
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLException
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.io.File
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean

object QueueManager {
    private lateinit var app: Context
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val persistMutex = Mutex()

    private val _jobs = MutableStateFlow<List<Job>>(emptyList())
    val jobs: StateFlow<List<Job>> = _jobs.asStateFlow()

    private val _history = MutableStateFlow<List<HistoryEntry>>(emptyList())
    val history: StateFlow<List<HistoryEntry>> = _history.asStateFlow()

    private val running = AtomicBoolean(false)

    private val speedRegex = Regex("""at\s+([\d.]+)\s*([KMG])iB/s""", RegexOption.IGNORE_CASE)
    private val processingTags = listOf(
        "[Merger]", "[ExtractAudio]", "[VideoConvertor]", "[Metadata]",
        "[EmbedThumbnail]", "[FixupM3u8]", "[FixupM4a]", "[MoveFiles]",
    )

    fun init(context: Context) {
        app = context.applicationContext
        val stored = Store.loadJobs(app)
        _jobs.value = stored.map {
            if (it.status == JobStatus.DOWNLOADING || it.status == JobStatus.PROCESSING) {
                it.copy(status = JobStatus.QUEUED, progress = 0f, speed = 0, eta = 0, stage = "Queued")
            } else {
                it
            }
        }.filter { it.status == JobStatus.QUEUED }
        _history.value = Store.loadHistory(app)
    }

    fun resume() {
        if (_jobs.value.any { it.status == JobStatus.QUEUED }) pump()
    }

    fun enqueue(job: Job) {
        _jobs.update { it + job }
        persist()
        pump()
    }

    fun cancel(id: String) {
        val job = _jobs.value.firstOrNull { it.id == id } ?: return
        if (job.status == JobStatus.DOWNLOADING || job.status == JobStatus.PROCESSING) {
            Engine.cancel(id)
        } else if (job.status == JobStatus.QUEUED) {
            _jobs.update { list ->
                list.map {
                    if (it.id == id) it.copy().also { j ->
                        j.status = JobStatus.CANCELLED
                        j.stage = "Cancelled"
                    } else it
                }
            }
            persist()
        }
    }

    fun clearFinished() {
        _jobs.update { list ->
            list.filter { it.status == JobStatus.QUEUED || it.status == JobStatus.DOWNLOADING || it.status == JobStatus.PROCESSING }
        }
        persist()
    }

    fun removeHistory(entry: HistoryEntry) {
        _history.update { list -> list.filter { it.id != entry.id } }
        Store.saveHistory(app, _history.value)
    }

    private fun pump() {
        if (!running.compareAndSet(false, true)) return
        DownloadService.start(app)
        scope.launch {
            try {
                while (true) {
                    val next = _jobs.value.firstOrNull { it.status == JobStatus.QUEUED } ?: break
                    mark(next.id, persist = true) {
                        it.status = JobStatus.DOWNLOADING
                        it.stage = "Starting…"
                        it.progress = 0f
                        it.speed = 0
                        it.eta = 0
                        it.downloaded = 0
                    }
                    runJob(next.id)
                }
            } finally {
                running.set(false)
                if (_jobs.value.any { it.status == JobStatus.QUEUED }) {
                    pump()
                } else {
                    DownloadService.stop(app)
                }
            }
        }
    }

    private fun runJob(id: String) {
        val job = _jobs.value.firstOrNull { it.id == id } ?: return
        val prefs = Prefs(app)
        val dir = File(app.cacheDir, "tf/$id").apply { mkdirs() }

        try {
            Engine.ensure(app)
            val request = YoutubeDLRequest(job.url)
            request.addOption("--no-playlist")
            request.addOption("--playlist-items", "1")
            request.addOption("--newline")
            request.addOption("--no-mtime")
            request.addOption("--no-part")
            request.addOption("-o", File(dir, "%(title).120B.%(ext)s").absolutePath)
            if (prefs.proxy.isNotBlank()) request.addOption("--proxy", prefs.proxy.trim())

            if (job.kind == "audio") {
                request.addOption("-f", "ba/b")
                request.addOption("-x")
                request.addOption("--audio-format", job.fmt)
                request.addOption("--audio-quality", if (job.fmt == "mp3") "320K" else "0")
            } else {
                request.addOption("-f", videoFilter(job))
                request.addOption("--merge-output-format", job.fmt)
            }
            if (prefs.embedMeta) request.addOption("--embed-metadata")
            if (prefs.embedThumb && job.fmt != "wav") request.addOption("--embed-thumbnail")

            var lastTick = 0L
            YoutubeDL.getInstance().execute(request, id) { progress, eta, line ->
                if (processingTags.any { line.contains(it) }) {
                    mark(id) {
                        if (it.status != JobStatus.PROCESSING) {
                            it.status = JobStatus.PROCESSING
                            it.stage = "Processing…"
                            it.progress = 99f
                        }
                    }
                }
                val now = SystemClock.elapsedRealtime()
                if (now - lastTick >= 250L || progress >= 99.9f) {
                    lastTick = now
                    val pct = progress.coerceIn(0f, 100f)
                    val speed = parseSpeed(line)
                    mark(id) {
                        it.progress = pct
                        it.speed = speed
                        it.eta = eta.toInt()
                        if (it.status == JobStatus.DOWNLOADING) {
                            it.stage = "Downloading…"
                            if (it.total > 0 && pct < 100f) {
                                it.downloaded = (it.total * pct / 100.0).toLong()
                            }
                        }
                    }
                }
            }

            val produced = newestFile(dir)
                ?: throw IllegalStateException("The download finished but no file was produced.")
            val uri = MediaSaver.publish(app, produced)
                ?: throw IllegalStateException("Could not save the file into Downloads.")
            val size = produced.length()
            val fileName = produced.name
            val mime = Format.mimeFor(Format.extensionFromName(fileName))

            mark(id, persist = true) {
                it.status = JobStatus.DONE
                it.progress = 100f
                it.stage = "Complete"
                it.fileName = fileName
                it.uri = uri.toString()
                it.size = size
                it.downloaded = size
                it.total = size
                it.totalEstimated = false
                it.speed = 0
                it.eta = 0
            }

            val finished = _jobs.value.firstOrNull { it.id == id }
            if (finished != null) {
                addHistory(
                    HistoryEntry(
                        id = finished.id,
                        title = finished.title,
                        url = finished.url,
                        label = Format.formatLabel(finished.fmt, finished.kind),
                        size = size,
                        uri = uri.toString(),
                        fileName = fileName,
                        mime = mime,
                    ),
                )
                Notify.finished(app, finished.title, fileName)
            }
        } catch (e: YoutubeDL.CanceledException) {
            mark(id) {
                it.status = JobStatus.CANCELLED
                it.stage = "Cancelled"
                it.speed = 0
                it.eta = 0
            }
        } catch (e: Throwable) {
            val message = Engine.friendly(e.message ?: e.javaClass.simpleName)
            mark(id, persist = true) {
                it.status = JobStatus.ERROR
                it.stage = "Failed"
                it.error = message
                it.speed = 0
                it.eta = 0
            }
            val failed = _jobs.value.firstOrNull { it.id == id }
            Notify.failed(app, failed?.title ?: "Download", message)
        } finally {
            runCatching { dir.deleteRecursively() }
        }
    }

    private fun videoFilter(job: Job): String {
        val height = job.quality.toIntOrNull()
        val cap = if (height != null) "[height<=$height]" else ""
        return when (job.fmt.lowercase(Locale.US)) {
            "mp4" -> "bv*$cap[ext=mp4]+ba[ext=m4a]/bv*$cap+ba/b$cap/b"
            "webm" -> "bv*$cap[ext=webm]+ba[ext=webm]/bv*$cap+ba/b$cap/b"
            else -> "bv*$cap+ba/b$cap/b"
        }
    }

    private fun newestFile(dir: File): File? = dir.listFiles()
        ?.filter { it.isFile && !it.name.endsWith(".part") && !it.name.endsWith(".ytdl") && !it.name.endsWith(".temp") }
        ?.maxByOrNull { it.lastModified() }

    private fun parseSpeed(line: String): Long {
        val match = speedRegex.find(line) ?: return 0
        val value = match.groupValues[1].toDoubleOrNull() ?: return 0
        val unit = match.groupValues[2].uppercase(Locale.US)
        val factor = when (unit) {
            "K" -> 1024.0
            "M" -> 1024.0 * 1024.0
            "G" -> 1024.0 * 1024.0 * 1024.0
            else -> 1.0
        }
        return (value * factor).toLong()
    }

    private fun mark(id: String, persist: Boolean = false, block: (Job) -> Unit) {
        _jobs.update { list ->
            list.map { job ->
                if (job.id == id) job.copy().also(block) else job
            }
        }
        if (persist) persist()
    }

    private fun persist() {
        scope.launch {
            persistMutex.withLock {
                // Keep queued *and* in-flight jobs so a process kill mid-download
                // can be resumed on the next launch instead of silently lost.
                Store.saveJobs(
                    app,
                    _jobs.value.filter {
                        it.status == JobStatus.QUEUED ||
                            it.status == JobStatus.DOWNLOADING ||
                            it.status == JobStatus.PROCESSING
                    },
                )
            }
        }
    }

    private fun addHistory(entry: HistoryEntry) {
        _history.update { list -> (listOf(entry) + list).take(200) }
        Store.saveHistory(app, _history.value)
    }
}
