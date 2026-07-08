package com.example.slidebeautifier.model

data class TaskStatusResponse(
    val taskId: String,
    val status: String,
    val progress: Int,
    val previewImages: List<String>,
    val downloadUrl: String?,
    val message: String?
)