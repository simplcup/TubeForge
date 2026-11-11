package com.tubeforge.mobile

import android.content.Context
import org.json.JSONArray
import java.io.File

object Store {
    private fun file(context: Context, name: String) = File(context.filesDir, name)

    fun saveJobs(context: Context, jobs: List<Job>) {
        runCatching {
            val arr = JSONArray()
            jobs.forEach { arr.put(it.toJson()) }
            writeAtomic(file(context, "queue.json"), arr.toString())
        }
    }

    fun loadJobs(context: Context): List<Job> = runCatching {
        val raw = file(context, "queue.json").takeIf { it.isFile }?.readText() ?: return emptyList()
        val arr = JSONArray(raw)
        (0 until arr.length()).map { Job.fromJson(arr.getJSONObject(it)) }
    }.getOrDefault(emptyList())

    fun saveHistory(context: Context, items: List<HistoryEntry>) {
        runCatching {
            writeAtomic(file(context, "history.json"), HistoryEntry.listToJson(items))
        }
    }

    fun loadHistory(context: Context): List<HistoryEntry> = runCatching {
        val raw = file(context, "history.json").takeIf { it.isFile }?.readText() ?: return emptyList()
        HistoryEntry.listFromJson(raw)
    }.getOrDefault(emptyList())

    private fun writeAtomic(target: File, text: String) {
        val tmp = File(target.parentFile, target.name + ".tmp")
        tmp.writeText(text)
        if (!tmp.renameTo(target)) {
            target.delete()
            tmp.renameTo(target)
        }
    }
}
