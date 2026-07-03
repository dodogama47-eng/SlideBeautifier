package com.example.slidebeautifier.network

data class OpenAIResponseRequest(
    val model: String,
    val input: String
)

data class OpenAIResponseBody(
    val output_text: String? = null
)