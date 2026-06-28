package com.example.sildebeautifier.model

data class Presentation(
    val id: String = "",
    val userId: String = "",
    val title: String = "",
    val inputText: String = "",
    val templateUrl: String = "",
    val outputUrl: String = "",
    val status: String = "created",
    val createdAt: Long = System.currentTimeMillis()
)