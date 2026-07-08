package com.example.slidebeautifier.repository

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import com.example.slidebeautifier.model.BeautifyResponse
import com.example.slidebeautifier.network.RetrofitClient
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

class BeautifyRepository {

    suspend fun uploadSlides(
        context: Context,
        originalUri: Uri,
        styleUri: Uri
    ): BeautifyResponse {
        val originalPart = uriToMultipart(
            context = context,
            uri = originalUri,
            partName = "original_file"
        )

        val stylePart = uriToMultipart(
            context = context,
            uri = styleUri,
            partName = "style_file"
        )

        return RetrofitClient.beautifyApi.uploadSlides(
            originalFile = originalPart,
            styleFile = stylePart
        )
    }

    private fun uriToMultipart(
        context: Context,
        uri: Uri,
        partName: String
    ): MultipartBody.Part {
        val contentResolver = context.contentResolver

        val fileName = getFileName(context, uri) ?: "upload.pptx"

        val mimeType = contentResolver.getType(uri)
            ?: "application/vnd.openxmlformats-officedocument.presentationml.presentation"

        val inputStream = contentResolver.openInputStream(uri)
            ?: throw IllegalArgumentException("Cannot open selected file")

        val fileBytes = inputStream.use {
            it.readBytes()
        }

        val requestBody = fileBytes.toRequestBody(
            mimeType.toMediaTypeOrNull()
        )

        return MultipartBody.Part.createFormData(
            partName,
            fileName,
            requestBody
        )
    }

    private fun getFileName(
        context: Context,
        uri: Uri
    ): String? {
        val cursor = context.contentResolver.query(
            uri,
            null,
            null,
            null,
            null
        )

        cursor?.use {
            val nameIndex = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (it.moveToFirst() && nameIndex >= 0) {
                return it.getString(nameIndex)
            }
        }

        return null
    }
}