package com.example.slidebeautifier.model

data class GenerateResponse(
    val task_id: String,
    val status: String,
    val download_url: String?,
    val original_preview_images: List<String> = emptyList(),
    val reference_preview_images: List<String> = emptyList(),
    val beautified_preview_images: List<String> = emptyList()
)