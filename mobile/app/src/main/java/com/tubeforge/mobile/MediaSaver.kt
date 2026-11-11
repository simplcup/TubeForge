package com.tubeforge.mobile

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import java.io.File

object MediaSaver {
    private const val FOLDER = "TubeForge"

    /** Copies a finished file into shared Downloads/TubeForge and returns its Uri. */
    fun publish(context: Context, file: File): Uri? {
        val resolver = context.contentResolver
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, file.name)
            put(MediaStore.MediaColumns.MIME_TYPE, Format.mimeFor(Format.extensionFromName(file.name)))
            put(
                MediaStore.MediaColumns.RELATIVE_PATH,
                Environment.DIRECTORY_DOWNLOADS + File.separator + FOLDER,
            )
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }

        val collection = MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        val uri = resolver.insert(collection, values) ?: return null

        return try {
            resolver.openOutputStream(uri)?.use { out ->
                file.inputStream().use { input -> input.copyTo(out, 128 * 1024) }
            } ?: throw IllegalStateException("Could not open Downloads file")

            val ready = ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }
            resolver.update(uri, ready, null, null)
            uri
        } catch (e: Throwable) {
            runCatching { resolver.delete(uri, null, null) }
            null
        }
    }

    fun mimeFor(name: String): String = Format.mimeFor(Format.extensionFromName(name))
}
