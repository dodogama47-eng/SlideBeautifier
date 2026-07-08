package com.example.slidebeautifier.network

data class GenerateResponse(
    val task_id: String,
    val status: String,
    val download_url: String
)