package com.example.slidebeautifier.model

data class PreviewResultData(
    val taskId: String,
    val originalPreviewImages: List<String>,
    val referencePreviewImages: List<String>,
    val beautifiedPreviewImages: List<String>,
    val downloadUrl: String?
)