package com.tubeforge.mobile

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class JobAdapter(
    private val onAction: (Job) -> Unit,
) : RecyclerView.Adapter<JobAdapter.VH>() {

    var palette: Palette = Palettes.all.first()
    private var items: List<Job> = emptyList()

    fun submit(list: List<Job>) {
        items = list
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_job, parent, false)
        return VH(view)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        holder.bind(items[position], palette, onAction)
    }

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        private val root: View = view.findViewById(R.id.job_root)
        private val title: TextView = view.findViewById(R.id.job_title)
        private val meta: TextView = view.findViewById(R.id.job_meta)
        private val status: TextView = view.findViewById(R.id.job_status)
        private val progress: ProgressBar = view.findViewById(R.id.job_progress)
        private val action: ImageView = view.findViewById(R.id.job_action)

        fun bind(job: Job, palette: Palette, onAction: (Job) -> Unit) {
            root.background = ThemeUi.round(palette.card, palette.border, 16f)
            title.setTextColor(palette.text)
            meta.setTextColor(palette.muted)

            title.text = job.title
            meta.text = buildMeta(job)

            status.text = when (job.status) {
                JobStatus.QUEUED -> "Queued"
                JobStatus.DOWNLOADING -> "${job.progress.toInt()}%"
                JobStatus.PROCESSING -> "Processing"
                JobStatus.DONE -> "Done"
                JobStatus.ERROR -> "Failed"
                JobStatus.CANCELLED -> "Cancelled"
            }
            status.setTextColor(
                when (job.status) {
                    JobStatus.ERROR -> palette.danger
                    JobStatus.DONE -> palette.success
                    JobStatus.CANCELLED -> palette.muted
                    else -> palette.accent
                },
            )

            progress.progressTintList =
                android.content.res.ColorStateList.valueOf(
                    if (job.status == JobStatus.ERROR) palette.danger else palette.accent,
                )
            progress.progressBackgroundTintList =
                android.content.res.ColorStateList.valueOf(palette.border)
            progress.progress = job.progress.toInt()
            progress.visibility = if (job.status == JobStatus.QUEUED) View.INVISIBLE else View.VISIBLE

            val canCancel = job.status == JobStatus.QUEUED ||
                job.status == JobStatus.DOWNLOADING ||
                job.status == JobStatus.PROCESSING
            action.visibility = if (canCancel) View.VISIBLE else View.GONE
            action.setColorFilter(palette.dim)
            action.setOnClickListener { onAction(job) }
        }

        private fun buildMeta(job: Job): String {
            val label = Format.formatLabel(job.fmt, job.kind)
            val detail = mutableListOf<String>()
            when (job.status) {
                JobStatus.QUEUED -> detail.add("Waiting…")
                JobStatus.DOWNLOADING -> {
                    if (job.speed > 0) detail.add(Format.speed(job.speed))
                    if (job.eta > 0) detail.add("ETA ${Format.eta(job.eta)}")
                    if (job.total > 0) {
                        val total = (if (job.totalEstimated) "~" else "") + Format.bytes(job.total)
                        detail.add("${Format.bytes(job.downloaded)} / $total")
                    }
                }
                JobStatus.PROCESSING -> detail.add("Processing…")
                JobStatus.DONE -> {
                    detail.add(Format.bytes(job.size))
                    detail.add("Complete")
                }
                JobStatus.ERROR -> detail.add(job.error.ifBlank { "Download failed" })
                JobStatus.CANCELLED -> detail.add("Cancelled")
            }
            return if (detail.isEmpty()) label else "$label  ·  " + detail.joinToString("  ·  ")
        }
    }
}
