package com.example.slidebeautifier.repository

import android.content.Context
import android.net.Uri
import java.io.File
import java.util.UUID

class LocalStorageRepository(
    private val context: Context
) {
    private val uploadsDir = File(context.filesDir, "uploads")
    private val resultsDir = File(context.filesDir, "results")

    init {
        uploadsDir.mkdirs()
        resultsDir.mkdirs()
    }

    fun saveUploadedFile(uri: Uri, prefix: String): File {
        val fileName = "${prefix}_${UUID.randomUUID()}.pptx"
        val outputFile = File(uploadsDir, fileName)

        context.contentResolver.openInputStream(uri)?.use { input ->
            outputFile.outputStream().use { output ->
                input.copyTo(output)
            }
        }

        return outputFile
    }

    fun createResultFile(): File {
        return File(resultsDir, "result_${System.currentTimeMillis()}.pptx")
    }

    fun getUploadsDir(): File = uploadsDir

    fun getResultsDir(): File = resultsDir
}