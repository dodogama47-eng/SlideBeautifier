package com.example.slidebeautifier.repository

import com.example.slidebeautifier.data.Constants
import android.content.Context
import android.net.Uri
import android.os.Environment
import com.example.slidebeautifier.network.BackendClient
import com.example.slidebeautifier.model.GenerateResponse
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import android.content.ContentValues
import android.provider.MediaStore
class BackendRepository(
    private val context: Context
) {

    suspend fun uploadFiles(
        formatUri: Uri,
        textUri: Uri
    ): GenerateResponse {
        val formatPart = createFilePart(
            uri = formatUri,
            partName = "format_file",
            fileName = "format.pptx"
        )

        val textPart = createFilePart(
            uri = textUri,
            partName = "text_file",
            fileName = "content.pptx"
        )

        return BackendClient.service.generatePpt(
            formatFile = formatPart,
            textFile = textPart
        )
    }

    suspend fun downloadResult(downloadUrl: String, taskId: String): String {
        val fullUrl = if (downloadUrl.startsWith("http")) {
            downloadUrl
        } else {
            Constants.BACKEND_BASE_URL.trimEnd('/') + downloadUrl
        }

        val responseBody = BackendClient.service.downloadFile(fullUrl)

        val fileName = "SlideBeautifier_$taskId.pptx"

        val resolver = context.contentResolver

        val contentValues = ContentValues()

        contentValues.put(MediaStore.Downloads.DISPLAY_NAME, fileName)
        contentValues.put(
            MediaStore.Downloads.MIME_TYPE,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        contentValues.put(
            MediaStore.Downloads.RELATIVE_PATH,
            Environment.DIRECTORY_DOWNLOADS
        )
        val uri = resolver.insert(
            MediaStore.Downloads.EXTERNAL_CONTENT_URI,
            contentValues
        ) ?: throw Exception("Failed to create download file")

        resolver.openOutputStream(uri)?.use { outputStream ->
            responseBody.byteStream().use { inputStream ->
                inputStream.copyTo(outputStream)
            }
        } ?: throw Exception("Failed to open output stream")

        return fileName
    }

    private fun createFilePart(
        uri: Uri,
        partName: String,
        fileName: String
    ): MultipartBody.Part {
        val contentResolver = context.contentResolver

        val mimeType = contentResolver.getType(uri)
            ?: "application/vnd.openxmlformats-officedocument.presentationml.presentation"

        val bytes = contentResolver.openInputStream(uri)?.use { inputStream ->
            inputStream.readBytes()
        } ?: throw IllegalArgumentException("Cannot open selected file")

        if (bytes.isEmpty()) {
            throw IllegalArgumentException("Selected file is empty or unreadable")
        }

        android.util.Log.d(
            "UploadDebug",
            "$partName size = ${bytes.size}, mimeType = $mimeType"
        )

        val requestBody = bytes.toRequestBody(
            mimeType.toMediaTypeOrNull(),
            0,
            bytes.size
        )

        return MultipartBody.Part.createFormData(
            partName,
            fileName,
            requestBody
        )
    }
    }