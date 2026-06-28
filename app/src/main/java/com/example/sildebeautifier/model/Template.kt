package com.example.sildebeautifier.model

data class Template(
    val id: String = "",
    val userId: String = "",
    val fileName: String = "",
    val fileUrl: String = "",
    val uploadedAt: Long = System.currentTimeMillis()
)