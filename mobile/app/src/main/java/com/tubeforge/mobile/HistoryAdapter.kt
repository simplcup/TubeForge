package com.tubeforge.mobile

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class HistoryAdapter(
    private val onOpen: (HistoryEntry) -> Unit,
) : RecyclerView.Adapter<HistoryAdapter.VH>() {

    var palette: Palette = Palettes.all.first()
    private var items: List<HistoryEntry> = emptyList()

    fun submit(list: List<HistoryEntry>) {
        items = list
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_history, parent, false)
        return VH(view)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        holder.bind(items[position], palette, onOpen)
    }

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        private val root: View = view.findViewById(R.id.hist_root)
        private val title: TextView = view.findViewById(R.id.hist_title)
        private val meta: TextView = view.findViewById(R.id.hist_meta)
        private val open: TextView = view.findViewById(R.id.hist_open)

        fun bind(entry: HistoryEntry, palette: Palette, onOpen: (HistoryEntry) -> Unit) {
            root.background = ThemeUi.round(palette.card, palette.border, 16f)
            title.setTextColor(palette.text)
            meta.setTextColor(palette.muted)

            title.text = entry.title

            val bits = mutableListOf<String>()
            if (entry.label.isNotBlank()) bits.add(entry.label)
            if (entry.size > 0) bits.add(Format.bytes(entry.size))
            bits.add(Format.date(entry.createdAt))
            meta.text = bits.joinToString("  ·  ")

            open.background = ThemeUi.round(palette.card2, palette.border, 10f)
            open.setTextColor(palette.text)
            open.setOnClickListener { onOpen(entry) }
        }
    }
}
