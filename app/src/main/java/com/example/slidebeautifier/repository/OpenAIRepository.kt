package com.example.slidebeautifier.repository

import com.example.slidebeautifier.BuildConfig
import com.example.slidebeautifier.data.Constants
import com.example.slidebeautifier.network.OpenAIClient
import com.example.slidebeautifier.network.OpenAIResponseRequest

class OpenAIRepository {

    suspend fun generateSlidePlan(userText: String): String {
        val prompt = """
            You are an AI PowerPoint layout assistant.

            Split the user's raw text into presentation slides.

            Return the result in this exact format:

            Slide 1:
            Title:
            Bullets:

            Slide 2:
            Title:
            Bullets:

            User text:
            $userText
        """.trimIndent()

        val response = OpenAIClient.service.createResponse(
            authorization = "Bearer ${BuildConfig.OPENAI_API_KEY}",
            request = OpenAIResponseRequest(
                model = Constants.OPENAI_MODEL,
                input = prompt
            )
        )

        return response.output_text ?: ""
    }
}