package com.tubeforge.mobile

import android.Manifest
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.text.TextUtils
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.URL
import java.util.Locale
import java.util.UUID

class MainActivity : AppCompatActivity() {

    private lateinit var prefs: Prefs
    private lateinit var palette: Palette

    private var page = 0
    private var media: MediaInfo? = null
    private var kind = "audio"
    private var fmt = "mp3"
    private var quality = "best"
    private var fetching = false
    private var updating = false

    private lateinit var jobAdapter: JobAdapter
    private lateinit var historyAdapter: HistoryAdapter

    private lateinit var root: View
    private lateinit var pageDownload: View
    private lateinit var pageQueue: View
    private lateinit var pageHistory: View
    private lateinit var pageSettings: View

    private lateinit var navDownload: View
    private lateinit var navQueue: View
    private lateinit var navHistory: View
    private lateinit var navSettings: View
    private lateinit var navIconDownload: ImageView
    private lateinit var navIconQueue: ImageView
    private lateinit var navIconHistory: ImageView
    private lateinit var navIconSettings: ImageView
    private lateinit var navLabelDownload: TextView
    private lateinit var navLabelQueue: TextView
    private lateinit var navLabelHistory: TextView
    private lateinit var navLabelSettings: TextView
    private lateinit var navBadge: TextView

    private lateinit var dlUrl: EditText
    private lateinit var dlPaste: TextView
    private lateinit var dlFetch: TextView
    private lateinit var dlError: TextView
    private lateinit var dlEmptyCard: View
    private lateinit var dlPreviewCard: View
    private lateinit var dlThumb: ImageView
    private lateinit var dlTitle: TextView
    private lateinit var dlMeta: TextView
    private lateinit var dlChipSource: TextView
    private lateinit var dlAudioRow: LinearLayout
    private lateinit var dlVideoRow: LinearLayout
    private lateinit var dlQualityWrap: View
    private lateinit var dlQualityRow: LinearLayout
    private lateinit var dlSelection: TextView
    private lateinit var dlDownload: TextView

    private lateinit var qClear: TextView
    private lateinit var qSummary: TextView
    private lateinit var qList: RecyclerView
    private lateinit var qEmpty: TextView

    private lateinit var hSummary: TextView
    private lateinit var hList: RecyclerView
    private lateinit var hEmpty: TextView

    private lateinit var sThemeGrid: LinearLayout
    private lateinit var sProxy: EditText
    private lateinit var sEmbedThumb: SwitchCompat
    private lateinit var sEmbedMeta: SwitchCompat
    private lateinit var sEngineVersion: TextView
    private lateinit var sUpdate: TextView
    private lateinit var sLicences: TextView
    private lateinit var sFooter: TextView

    private val audioFormats = listOf(
        Triple("mp3", "MP3", "320 kbps"),
        Triple("m4a", "M4A", "AAC audio"),
        Triple("opus", "OPUS", "original"),
        Triple("flac", "FLAC", "lossless"),
        Triple("wav", "WAV", "uncompressed"),
    )
    private val videoFormats = listOf(
        Triple("mp4", "MP4", "H.264"),
        Triple("webm", "WEBM", "VP9"),
        Triple("mkv", "MKV", "any codec"),
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        palette = Palettes.get(prefs.themeId)

        val last = prefs.lastFormat
        if (videoFormats.any { it.first == last }) {
            kind = "video"
            fmt = last
        } else {
            kind = "audio"
            fmt = audioFormats.firstOrNull { it.first == last }?.first ?: "mp3"
        }
        quality = prefs.lastQuality

        setContentView(R.layout.activity_main)
        WindowCompat.setDecorFitsSystemWindows(window, false)

        bindViews()
        setupInsets()
        setupLists()
        setupNav()
        setupDownload()
        setupQueue()
        setupHistory()
        setupSettings()
        setupFlows()
        setupBack()

        refreshTheme()
        switchPage(0)
        requestNotificationPermission()
        loadEngineVersion()
        handleShareIntent(intent)
    }

    override fun onStart() {
        super.onStart()
        // Resuming here (rather than in Application.onCreate) keeps the
        // foreground-service start inside a user-visible activity launch,
        // which Android 12+ requires.
        QueueManager.resume()
    }

    private fun bindViews() {
        root = findViewById(R.id.root)
        pageDownload = findViewById(R.id.page_download)
        pageQueue = findViewById(R.id.page_queue)
        pageHistory = findViewById(R.id.page_history)
        pageSettings = findViewById(R.id.page_settings)

        navDownload = findViewById(R.id.nav_download)
        navQueue = findViewById(R.id.nav_queue)
        navHistory = findViewById(R.id.nav_history)
        navSettings = findViewById(R.id.nav_settings)
        navIconDownload = findViewById(R.id.nav_icon_download)
        navIconQueue = findViewById(R.id.nav_icon_queue)
        navIconHistory = findViewById(R.id.nav_icon_history)
        navIconSettings = findViewById(R.id.nav_icon_settings)
        navLabelDownload = findViewById(R.id.nav_label_download)
        navLabelQueue = findViewById(R.id.nav_label_queue)
        navLabelHistory = findViewById(R.id.nav_label_history)
        navLabelSettings = findViewById(R.id.nav_label_settings)
        navBadge = findViewById(R.id.nav_badge)

        dlUrl = findViewById(R.id.dl_url_edit)
        dlPaste = findViewById(R.id.dl_paste)
        dlFetch = findViewById(R.id.dl_fetch)
        dlError = findViewById(R.id.dl_error)
        dlEmptyCard = findViewById(R.id.dl_empty_card)
        dlPreviewCard = findViewById(R.id.dl_preview_card)
        dlThumb = findViewById(R.id.dl_thumb)
        dlTitle = findViewById(R.id.dl_title)
        dlMeta = findViewById(R.id.dl_meta)
        dlChipSource = findViewById(R.id.dl_chip_source)
        dlAudioRow = findViewById(R.id.dl_audio_row)
        dlVideoRow = findViewById(R.id.dl_video_row)
        dlQualityWrap = findViewById(R.id.dl_quality_wrap)
        dlQualityRow = findViewById(R.id.dl_quality_row)
        dlSelection = findViewById(R.id.dl_selection)
        dlDownload = findViewById(R.id.dl_download)

        qClear = findViewById(R.id.q_clear)
        qSummary = findViewById(R.id.q_summary)
        qList = findViewById(R.id.q_list)
        qEmpty = findViewById(R.id.q_empty)

        hSummary = findViewById(R.id.h_summary)
        hList = findViewById(R.id.h_list)
        hEmpty = findViewById(R.id.h_empty)

        sThemeGrid = findViewById(R.id.s_theme_grid)
        sProxy = findViewById(R.id.s_proxy)
        sEmbedThumb = findViewById(R.id.s_embed_thumb)
        sEmbedMeta = findViewById(R.id.s_embed_meta)
        sEngineVersion = findViewById(R.id.s_engine_version)
        sUpdate = findViewById(R.id.s_update)
        sLicences = findViewById(R.id.s_licences)
        sFooter = findViewById(R.id.s_footer)
    }

    private fun setupInsets() {
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            val ime = insets.getInsets(WindowInsetsCompat.Type.ime())
            view.setPadding(bars.left, bars.top, bars.right, maxOf(bars.bottom, ime.bottom))
            insets
        }
    }

    private fun setupLists() {
        jobAdapter = JobAdapter { job -> QueueManager.cancel(job.id) }
        historyAdapter = HistoryAdapter { entry -> openHistory(entry) }

        qList.layoutManager = LinearLayoutManager(this)
        qList.adapter = jobAdapter
        qList.itemAnimator = null

        hList.layoutManager = LinearLayoutManager(this)
        hList.adapter = historyAdapter
        hList.itemAnimator = null
    }

    private fun setupNav() {
        navDownload.setOnClickListener { switchPage(0) }
        navQueue.setOnClickListener { switchPage(1) }
        navHistory.setOnClickListener { switchPage(2) }
        navSettings.setOnClickListener { switchPage(3) }
    }

    private fun setupBack() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (page != 0) {
                    switchPage(0)
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })
    }

    private fun switchPage(index: Int) {
        page = index
        pageDownload.visibility = if (index == 0) View.VISIBLE else View.GONE
        pageQueue.visibility = if (index == 1) View.VISIBLE else View.GONE
        pageHistory.visibility = if (index == 2) View.VISIBLE else View.GONE
        pageSettings.visibility = if (index == 3) View.VISIBLE else View.GONE
        updateNavColors()
    }

    private fun setupDownload() {
        dlPaste.setOnClickListener { pasteLink() }
        dlFetch.setOnClickListener { fetchMedia() }
        dlDownload.setOnClickListener { startDownload() }
        dlUrl.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_GO) {
                fetchMedia()
                true
            } else {
                false
            }
        }
        updateDownloadButton()
        renderFormatChips()
        renderQualityChips()
        updateSelectionLabel()
    }

    private fun setupQueue() {
        qClear.setOnClickListener {
            QueueManager.clearFinished()
            toast("Finished downloads cleared")
        }
    }

    private fun setupHistory() {
        hSummary.text = ""
    }

    private fun setupSettings() {
        sProxy.setText(prefs.proxy)
        sProxy.setOnFocusChangeListener { _, hasFocus ->
            if (!hasFocus) saveProxy()
        }
        sProxy.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                saveProxy()
                true
            } else {
                false
            }
        }

        sEmbedThumb.isChecked = prefs.embedThumb
        sEmbedMeta.isChecked = prefs.embedMeta
        sEmbedThumb.setOnCheckedChangeListener { _, checked -> prefs.embedThumb = checked }
        sEmbedMeta.setOnCheckedChangeListener { _, checked -> prefs.embedMeta = checked }

        sUpdate.setOnClickListener { updateEngine() }
        sLicences.setOnClickListener { showLicences() }

        sFooter.text = "TubeForge ${versionName()} · yt-dlp engine"
    }

    /** GPL-3.0 + Apache-2.0 notices must be readable from the shipped APK. */
    private fun showLicences() {
        lifecycleScope.launch {
            val body = withContext(Dispatchers.IO) {
                runCatching {
                    assets.open("licences/NOTICES.txt").bufferedReader().use { it.readText() }
                }.getOrNull()
            } ?: "The licence texts are bundled in the app package (assets/licences)."
            val density = resources.displayMetrics.density
            val pad = (16 * density).toInt()
            val view = TextView(this@MainActivity).apply {
                text = body
                textSize = 11.5f
                setPadding(pad, pad, pad, pad)
                setTextIsSelectable(true)
            }
            val scroll = android.widget.ScrollView(this@MainActivity).apply { addView(view) }
            androidx.appcompat.app.AlertDialog.Builder(this@MainActivity)
                .setTitle("Open-source licences")
                .setView(scroll)
                .setPositiveButton("Close", null)
                .show()
        }
    }

    private fun saveProxy() {
        prefs.proxy = sProxy.text.toString().trim()
    }

    private fun setupFlows() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch { QueueManager.jobs.collect { renderJobs(it) } }
                launch { QueueManager.history.collect { renderHistory(it) } }
            }
        }
    }

    private fun renderJobs(jobs: List<Job>) {
        jobAdapter.palette = palette
        jobAdapter.submit(jobs)

        val empty = jobs.isEmpty()
        qEmpty.visibility = if (empty) View.VISIBLE else View.GONE
        qList.visibility = if (empty) View.GONE else View.VISIBLE

        val active = jobs.count { it.status == JobStatus.DOWNLOADING || it.status == JobStatus.PROCESSING }
        val queued = jobs.count { it.status == JobStatus.QUEUED }
        qSummary.text = if (empty) {
            "One download at a time."
        } else {
            "$active active  ·  ${jobs.size} in this session  ·  one download at a time"
        }

        val pending = active + queued
        navBadge.visibility = if (pending > 0) View.VISIBLE else View.GONE
        navBadge.text = if (pending > 9) "9+" else pending.toString()
    }

    private fun renderHistory(items: List<HistoryEntry>) {
        historyAdapter.palette = palette
        historyAdapter.submit(items)

        val empty = items.isEmpty()
        hEmpty.visibility = if (empty) View.VISIBLE else View.GONE
        hList.visibility = if (empty) View.GONE else View.VISIBLE
        hSummary.text = if (empty) {
            "Finished files land in Download/TubeForge."
        } else {
            "${items.size} finished  ·  saved in Download/TubeForge"
        }
    }

    private fun refreshTheme() {
        palette = Palettes.get(prefs.themeId)
        ThemeUi.apply(this, window.decorView, palette)

        navBadge.background = ThemeUi.round(palette.accent, null, 99f)
        navBadge.setTextColor(palette.onAccent)

        styleSwitches()
        renderFormatChips()
        renderQualityChips()
        renderThemeGrid()
        updateSelectionLabel()
        updateNavColors()

        jobAdapter.palette = palette
        jobAdapter.notifyDataSetChanged()
        historyAdapter.palette = palette
        historyAdapter.notifyDataSetChanged()
    }

    private fun styleSwitches() {
        val thumb = ColorStateList(
            arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()),
            intArrayOf(palette.accent, palette.muted),
        )
        val track = ColorStateList(
            arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()),
            intArrayOf(palette.withAlpha(palette.accent, 0.55f), palette.border2),
        )
        listOf(sEmbedThumb, sEmbedMeta).forEach {
            it.thumbTintList = thumb
            it.trackTintList = track
        }
    }

    private fun updateNavColors() {
        val icons = listOf(navIconDownload, navIconQueue, navIconHistory, navIconSettings)
        val labels = listOf(navLabelDownload, navLabelQueue, navLabelHistory, navLabelSettings)
        icons.forEachIndexed { index, icon ->
            icon.setColorFilter(if (index == page) palette.accent else palette.dim)
        }
        labels.forEachIndexed { index, label ->
            label.setTextColor(if (index == page) palette.accent else palette.dim)
        }
    }

    // -- format chips ------------------------------------------------------

    private fun renderFormatChips() {
        dlAudioRow.removeAllViews()
        audioFormats.forEach { (id, name, sub) ->
            dlAudioRow.addView(
                chip(name, sub, kind == "audio" && fmt == id) {
                    kind = "audio"
                    fmt = id
                    prefs.lastFormat = id
                    onFormatChanged()
                },
            )
        }
        dlVideoRow.removeAllViews()
        videoFormats.forEach { (id, name, sub) ->
            dlVideoRow.addView(
                chip(name, sub, kind == "video" && fmt == id) {
                    kind = "video"
                    fmt = id
                    prefs.lastFormat = id
                    onFormatChanged()
                },
            )
        }
    }

    private fun onFormatChanged() {
        renderFormatChips()
        renderQualityChips()
        updateSelectionLabel()
        dlQualityWrap.visibility = if (kind == "video") View.VISIBLE else View.GONE
        updateDownloadButton()
    }

    private fun renderQualityChips() {
        dlQualityWrap.visibility = if (kind == "video") View.VISIBLE else View.GONE
        dlQualityRow.removeAllViews()
        qualityOptions().forEach { (value, label) ->
            val selected = quality == value
            val box = TextView(this).apply {
                text = label
                textSize = 12.5f
                setTypeface(typeface, android.graphics.Typeface.BOLD)
                setTextColor(if (selected) palette.accent else palette.text)
                setPadding(dp(14), dp(8), dp(14), dp(8))
                background = if (selected) {
                    ThemeUi.round(palette.accentSoft2, palette.accent, 12f)
                } else {
                    ThemeUi.round(palette.card2, palette.border, 12f)
                }
                isClickable = true
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                ).apply { marginEnd = dp(8) }
                setOnClickListener {
                    quality = value
                    prefs.lastQuality = value
                    renderQualityChips()
                    updateSelectionLabel()
                }
            }
            dlQualityRow.addView(box)
        }
    }

    private fun qualityOptions(): List<Pair<String, String>> {
        val options = mutableListOf("best" to "Best available")
        media?.videoHeights()?.take(8)?.forEach { options.add(it.toString() to "${it}p") }
        if (options.none { it.first == quality }) quality = "best"
        return options
    }

    private fun chip(name: String, sub: String, selected: Boolean, onClick: () -> Unit): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(13), dp(9), dp(13), dp(9))
            background = if (selected) {
                ThemeUi.round(palette.accentSoft2, palette.accent, 12f)
            } else {
                ThemeUi.round(palette.card2, palette.border, 12f)
            }
            isClickable = true
            isFocusable = true
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            ).apply { marginEnd = dp(8) }
            setOnClickListener { onClick() }
        }
        box.addView(
            TextView(this).apply {
                text = name
                textSize = 13.5f
                setTypeface(typeface, android.graphics.Typeface.BOLD)
                setTextColor(if (selected) palette.accent else palette.text)
            },
        )
        box.addView(
            TextView(this).apply {
                text = sub
                textSize = 10.5f
                setTextColor(palette.muted)
                setPadding(0, dp(1), 0, 0)
            },
        )
        return box
    }

    private fun updateSelectionLabel() {
        dlSelection.text = if (kind == "audio") {
            Format.formatLabel(fmt, "audio") + " · audio only"
        } else {
            val label = if (quality == "best") "Best available" else "${quality}p"
            "${fmt.uppercase(Locale.US)} · $label · video + audio"
        }
        dlSelection.setTextColor(palette.accent)
    }

    // -- theme grid --------------------------------------------------------

    private fun renderThemeGrid() {
        sThemeGrid.removeAllViews()
        var row: LinearLayout? = null
        Palettes.all.forEachIndexed { index, item ->
            if (index % 2 == 0) {
                row = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    layoutParams = LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                    )
                }
                sThemeGrid.addView(row)
            }
            val selected = item.id == palette.id
            val tile = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(10), dp(11), dp(10), dp(11))
                layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                    .apply {
                        marginEnd = dp(8)
                        topMargin = dp(8)
                    }
                background = if (selected) {
                    ThemeUi.round(item.accentSoft, item.accent, 12f)
                } else {
                    ThemeUi.round(item.card2, item.border, 12f)
                }
                isClickable = true
                setOnClickListener {
                    if (prefs.themeId != item.id) {
                        prefs.themeId = item.id
                        refreshTheme()
                    }
                }
            }
            tile.addView(
                View(this).apply {
                    layoutParams = LinearLayout.LayoutParams(dp(14), dp(14))
                    background = ThemeUi.round(item.accent, null, 99f)
                },
            )
            tile.addView(
                TextView(this).apply {
                    text = item.name.substringBefore(" (")
                    textSize = 11.5f
                    setTextColor(item.text)
                    setPadding(dp(8), 0, 0, 0)
                    maxLines = 1
                    ellipsize = TextUtils.TruncateAt.END
                },
            )
            row?.addView(tile)
        }
    }

    // -- fetch / download --------------------------------------------------

    private fun pasteLink() {
        val manager = getSystemService(ClipboardManager::class.java)
        val text = manager?.primaryClip
            ?.takeIf { it.itemCount > 0 }
            ?.getItemAt(0)
            ?.coerceToText(this)
            ?.toString()
            ?.trim()
        if (text.isNullOrBlank()) {
            toast("Clipboard is empty")
            return
        }
        dlUrl.setText(text)
        dlUrl.setSelection(dlUrl.text.length)
    }

    private fun fetchMedia() {
        if (fetching) return
        val url = normalizeUrl(dlUrl.text.toString())
        if (!isValidUrl(url)) {
            showError("Enter a valid link first.")
            return
        }
        fetching = true
        dlError.visibility = View.GONE
        dlFetch.text = "Fetching…"
        dlFetch.isEnabled = false
        dlFetch.alpha = 0.65f

        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching {
                    Engine.ensure(applicationContext)
                    Engine.fetch(url, prefs)
                }
            }
            fetching = false
            dlFetch.text = "Fetch"
            dlFetch.isEnabled = true
            dlFetch.alpha = 1f

            result.onSuccess { info ->
                media = info
                showPreview(info)
                updateDownloadButton()
            }.onFailure { error ->
                media = null
                hidePreview()
                updateDownloadButton()
                showError(Engine.friendly(error.message))
            }
        }
    }

    private fun showPreview(info: MediaInfo) {
        dlEmptyCard.visibility = View.GONE
        dlPreviewCard.visibility = View.VISIBLE
        dlTitle.text = info.title
        val bits = mutableListOf<String>()
        if (info.uploader.isNotBlank()) bits.add(info.uploader)
        if (info.duration > 0) bits.add(Format.duration(info.duration))
        bits.add("${info.formats.size} streams")
        dlMeta.text = bits.joinToString("  ·  ")
        dlChipSource.text = sourceLabel(info.url)
        dlChipSource.background = ThemeUi.round(palette.accentSoft, palette.accent, 99f)
        dlChipSource.setTextColor(palette.accent)
        dlThumb.setImageDrawable(null)

        if (info.thumbnail.isNotBlank()) {
            lifecycleScope.launch {
                val bitmap = withContext(Dispatchers.IO) {
                    runCatching {
                        val connection = URL(info.thumbnail).openConnection().apply {
                            connectTimeout = 15_000
                            readTimeout = 15_000
                        }
                        connection.getInputStream().use { BitmapFactory.decodeStream(it) }
                    }.getOrNull()
                }
                if (bitmap != null && media == info) dlThumb.setImageBitmap(bitmap)
            }
        }
    }

    private fun hidePreview() {
        dlPreviewCard.visibility = View.GONE
        dlEmptyCard.visibility = View.VISIBLE
    }

    private fun startDownload() {
        val info = media ?: run {
            toast("Fetch a link first")
            return
        }
        val (total, estimated) = estimateBytes(info)
        val job = Job(
            id = UUID.randomUUID().toString().replace("-", "").take(10),
            url = info.url,
            kind = kind,
            fmt = fmt,
            quality = if (kind == "video") quality else "best",
            title = info.title,
            uploader = info.uploader,
            duration = info.duration,
            thumbUrl = info.thumbnail,
            total = total,
            totalEstimated = estimated,
        )
        QueueManager.enqueue(job)
        toast("Added to queue")
        switchPage(1)
    }

    private fun estimateBytes(info: MediaInfo): Pair<Long, Boolean> {
        val duration = info.duration.toDouble()
        if (kind == "audio") {
            return when (fmt) {
                "mp3" -> (duration * 320_000.0 / 8 * 1.02).toLong() to true
                "m4a" -> (duration * 256_000.0 / 8 * 1.02).toLong() to true
                "flac" -> (duration * 44_100 * 2 * 2 * 0.55 * 1.02).toLong() to true
                "wav" -> (duration * 44_100 * 2 * 2 * 1.01 + 44).toLong() to true
                "opus" -> {
                    val src = info.audioFormats().maxByOrNull { it.abr }?.size ?: 0L
                    src to false
                }
                else -> 0L to false
            }
        }

        val height = quality.toIntOrNull()
        val video = info.formats
            .filter { it.isVideo && (height == null || it.height <= height) }
            .maxByOrNull { it.height.toLong() * 1000 + it.tbr }
        val audio = info.audioFormats().maxByOrNull { it.abr }
        val source = (video?.size ?: 0L) + (audio?.size ?: 0L)
        return (source * 1.01).toLong() to false
    }

    private fun updateDownloadButton() {
        val enabled = media != null && !fetching
        dlDownload.isEnabled = enabled
        dlDownload.alpha = if (enabled) 1f else 0.45f
    }

    private fun showError(message: String) {
        dlError.text = message
        dlError.setTextColor(palette.danger)
        dlError.visibility = View.VISIBLE
    }

    // -- history -----------------------------------------------------------

    private fun openHistory(entry: HistoryEntry) {
        val uri = Uri.parse(entry.uri)
        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, entry.mime)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        runCatching { startActivity(intent) }
            .onFailure { toast("No app on this phone can open ${entry.fileName}.") }
    }

    // -- settings ----------------------------------------------------------

    private fun loadEngineVersion() {
        sEngineVersion.text = "yt-dlp engine  ·  loading…"
        lifecycleScope.launch {
            val version = withContext(Dispatchers.IO) {
                runCatching {
                    Engine.ensure(applicationContext)
                    Engine.version(applicationContext)
                }.getOrDefault("unavailable")
            }
            sEngineVersion.text = "yt-dlp engine  ·  version $version"
            sEngineVersion.setTextColor(palette.text)
        }
    }

    private fun updateEngine() {
        if (updating) return
        updating = true
        sUpdate.isEnabled = false
        sUpdate.text = "Updating…"
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching { Engine.update(applicationContext) }
            }
            updating = false
            sUpdate.isEnabled = true
            sUpdate.text = "Update yt-dlp"
            result.onSuccess { version ->
                sEngineVersion.text = "yt-dlp engine  ·  version $version"
                toast("yt-dlp updated to $version")
            }.onFailure { error ->
                toast(Engine.friendly(error.message))
            }
        }
    }

    // -- misc --------------------------------------------------------------

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 11)
        }
    }

    private fun handleShareIntent(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val text = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim().orEmpty()
        if (text.isBlank()) return
        val url = Regex("""https?://\S+""").find(text)?.value ?: text
        dlUrl.setText(url)
        switchPage(0)
        fetchMedia()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleShareIntent(intent)
    }

    private fun normalizeUrl(raw: String): String {
        val text = raw.trim()
        if (text.isEmpty()) return text
        return if (text.contains("://")) text else "https://$text"
    }

    private fun isValidUrl(text: String): Boolean = runCatching {
        val uri = Uri.parse(text)
        (uri.scheme == "http" || uri.scheme == "https") && !uri.host.isNullOrBlank()
    }.getOrDefault(false)

    private fun sourceLabel(url: String): String {
        val host = runCatching { Uri.parse(url).host.orEmpty() }.getOrDefault("").lowercase(Locale.US)
        return when {
            host.contains("youtu") -> "YouTube"
            host.contains("soundcloud") -> "SoundCloud"
            host.contains("vimeo") -> "Vimeo"
            host.contains("tiktok") -> "TikTok"
            host.contains("instagram") -> "Instagram"
            host.contains("twitter") || host.contains("x.com") -> "X"
            host.contains("facebook") -> "Facebook"
            host.contains("reddit") -> "Reddit"
            host.contains("twitch") -> "Twitch"
            host.contains("dailymotion") -> "Dailymotion"
            host.isBlank() -> "Media"
            else -> host.removePrefix("www.").substringBefore(".")
        }
    }

    private fun versionName(): String = runCatching {
        packageManager.getPackageInfo(packageName, 0).versionName ?: "1.0.0"
    }.getOrDefault("1.0.0")

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }
}
