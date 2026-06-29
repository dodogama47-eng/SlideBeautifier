package com.example.slidebeautifier.repository

import com.example.slidebeautifier.model.Presentation
import com.example.slidebeautifier.model.Template
import com.google.firebase.firestore.FirebaseFirestore
import kotlinx.coroutines.tasks.await

class FirestoreRepository {

    private val db = FirebaseFirestore.getInstance()

    suspend fun saveTemplate(template: Template): String {
        val docRef = db.collection("templates").document()
        val newTemplate = template.copy(id = docRef.id)
        docRef.set(newTemplate).await()
        return docRef.id
    }

    suspend fun savePresentation(presentation: Presentation): String {
        val docRef = db.collection("presentations").document()
        val newPresentation = presentation.copy(id = docRef.id)
        docRef.set(newPresentation).await()
        return docRef.id
    }

    suspend fun updatePresentationOutput(
        presentationId: String,
        outputUrl: String
    ) {
        db.collection("presentations")
            .document(presentationId)
            .update(
                mapOf(
                    "outputUrl" to outputUrl,
                    "status" to "completed"
                )
            )
            .await()
    }

    suspend fun getUserPresentations(userId: String): List<Presentation> {
        val snapshot = db.collection("presentations")
            .whereEqualTo("userId", userId)
            .get()
            .await()

        return snapshot.documents.mapNotNull {
            it.toObject(Presentation::class.java)
        }
    }
}