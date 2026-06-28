package com.example.sildebeautifier.repository

import android.net.Uri
import com.google.firebase.storage.FirebaseStorage
import kotlinx.coroutines.tasks.await
import java.util.UUID

class StorageRepository{
    private val storage = FirebaseStorage.getInstance()

    suspend fun uploadTemplate(userId: String, fileUri: Uri, fileName: String): String{
        val  filePath = "templates/$userId/${UUID.randomUUID()}_$fileName"
        val ref = storage.reference.child(filePath)

        ref.putFile(fileUri).await()

        return ref.downloadUrl.await().toString()
    }

    suspend fun uploadGeneratePpt(userId: String, fileUri: Uri, fileName: String): String{
        val  filePath = "generated/$userId/${UUID.randomUUID()}_$fileName"
        val ref = storage.reference.child(filePath)

        ref.putFile(fileUri).await()

        return ref.downloadUrl.await().toString()
    }
}