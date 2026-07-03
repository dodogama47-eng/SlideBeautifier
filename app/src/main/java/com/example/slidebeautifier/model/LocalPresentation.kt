package com.example.slidebeautifier.model

data class LocalPresentation(
    val id: String = "",
    val templatePath: String = "",
    val contentPath: String = "",
    val resultPath: String = "",
    val status: String = "created",
    val createdAt: Long = System.currentTimeMillis()
)