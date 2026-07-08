package com.example.slidebeautifier.repository

import android.content.Context
import android.net.Uri
import com.example.slidebeautifier.network.BackendClient
import com.example.slidebeautifier.network.GenerateResponse
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

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

    private fun createFilePart(
        uri: Uri,
        partName: String,
        fileName: String
    ): MultipartBody.Part {
        val bytes = context.contentResolver.openInputStream(uri)?.use {
            it.readBytes()
        } ?: ByteArray(0)

        val requestBody = bytes.toRequestBody(
            "application/octet-stream".toMediaTypeOrNull()
        )

        return MultipartBody.Part.createFormData(
            partName,
            fileName,
            requestBody
        )
    }
}