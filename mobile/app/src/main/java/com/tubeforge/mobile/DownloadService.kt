package com.tubeforge.mobile

import android.app.Notification
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch

/**
 * Keeps the process alive while the queue works and mirrors progress into an
 * ongoing notification, so downloads survive leaving the app.
 */
class DownloadService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var collecting = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Notify.ensureChannel(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val initial = notification(null, "Preparing download…")
        ServiceCompat.startForeground(
            this,
            Notify.PROGRESS_ID,
            initial,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            } else {
                0
            },
        )

        if (!collecting) {
            collecting = true
            scope.launch {
                QueueManager.jobs.collect { jobs ->
                    val active = jobs.firstOrNull {
                        it.status == JobStatus.DOWNLOADING || it.status == JobStatus.PROCESSING
                    }
                    val pending = jobs.count { it.status == JobStatus.QUEUED }
                    if (active == null && pending == 0) {
                        stopForeground(STOP_FOREGROUND_REMOVE)
                        stopSelf()
                        return@collect
                    }
                    val text = when {
                        active == null -> "Waiting in queue…"
                        active.status == JobStatus.PROCESSING -> "Processing ${active.title}"
                        else -> active.title
                    }
                    runCatching {
                        NotificationManagerCompat.from(this@DownloadService)
                            .notify(Notify.PROGRESS_ID, notification(active, text))
                    }
                }
            }
        }
        return START_STICKY
    }

    private fun notification(job: Job?, text: String): Notification {
        val open = android.app.PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE,
        )

        val builder = NotificationCompat.Builder(this, Notify.CHANNEL)
            .setSmallIcon(R.drawable.ic_download)
            .setContentTitle("TubeForge")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)

        if (job != null) {
            builder.setProgress(100, job.progress.toInt(), job.progress <= 0f)
            val bits = mutableListOf<String>()
            if (job.speed > 0) bits.add(Format.speed(job.speed))
            if (job.eta > 0) bits.add("ETA ${Format.eta(job.eta)}")
            if (job.total > 0) {
                val total = (if (job.totalEstimated) "~" else "") + Format.bytes(job.total)
                bits.add("${Format.bytes(job.downloaded)} / $total")
            }
            if (bits.isNotEmpty()) builder.setSubText(bits.joinToString("  ·  "))
        }
        return builder.build()
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        fun start(context: Context) {
            runCatching {
                ContextCompat.startForegroundService(
                    context,
                    Intent(context, DownloadService::class.java),
                )
            }
        }

        fun stop(context: Context) {
            runCatching { context.stopService(Intent(context, DownloadService::class.java)) }
        }
    }
}
