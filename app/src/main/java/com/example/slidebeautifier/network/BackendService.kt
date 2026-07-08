package com.example.slidebeautifier.network

import okhttp3.MultipartBody
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface BackendService {

    @GET("/")
    suspend fun healthCheck(): Map<String, String>

    @Multipart
    @POST("generate")
    suspend fun generatePpt(
        @Part formatFile: MultipartBody.Part,
        @Part textFile: MultipartBody.Part
    ): GenerateResponse
}