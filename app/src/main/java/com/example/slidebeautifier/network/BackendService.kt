package com.example.slidebeautifier.network
import retrofit2.http.Streaming
import com.example.slidebeautifier.model.GenerateResponse
import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Url

interface BackendService {

    @GET("api/health")
    suspend fun healthCheck(): Map<String, String>

    @Multipart
    @POST("generate")
    suspend fun generatePpt(
        @Part formatFile: MultipartBody.Part,
        @Part textFile: MultipartBody.Part
    ): GenerateResponse
    @Streaming
    @GET
    suspend fun downloadFile(
        @Url fileUrl: String
    ): ResponseBody
}
