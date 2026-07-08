package com.example.slidebeautifier.network

import com.example.slidebeautifier.model.BeautifyResponse
import com.example.slidebeautifier.model.TaskStatusResponse
import okhttp3.MultipartBody
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

interface BeautifyApi {

    @Multipart
    @POST("api/beautify")
    suspend fun uploadSlides(
        @Part originalFile: MultipartBody.Part,
        @Part styleFile: MultipartBody.Part
    ): BeautifyResponse

    @GET("api/tasks/{taskId}")
    suspend fun getTaskStatus(
        @Path("taskId") taskId: String
    ): TaskStatusResponse
}