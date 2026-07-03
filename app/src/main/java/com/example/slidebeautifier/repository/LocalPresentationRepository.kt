package com.example.slidebeautifier.repository

import android.content.Context
import android.net.Uri
import com.example.slidebeautifier.model.LocalPresentation
import com.example.slidebeautifier.ppt.LocalPptProcessor
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

class LocalPresentationRepository(
    private val context: Context
) {
    private val storageRepository = LocalStorageRepository(context)
    private val pptProcessor = LocalPptProcessor()
    private val prefs = context.getSharedPreferences(
        "local_presentations",
        Context.MODE_PRIVATE
    )

    fun createPresentation(
        templateUri: Uri,
        contentUri: Uri
    ): LocalPresentation {
        val id = UUID.randomUUID().toString()

        val templateFile = storageRepository.saveUploadedFile(
            uri = templateUri,
            prefix = "template"
        )

        val contentFile = storageRepository.saveUploadedFile(
            uri = contentUri,
            prefix = "content"
        )

        val resultFile = storageRepository.createResultFile()

        pptProcessor.generateResultPpt(
            templateFile = templateFile,
            contentFile = contentFile,
            resultFile = resultFile
        )

        val presentation = LocalPresentation(
            id = id,
            templatePath = templateFile.absolutePath,
            contentPath = contentFile.absolutePath,
            resultPath = resultFile.absolutePath,
            status = "completed"
        )

        savePresentation(presentation)

        return presentation
    }

    private fun savePresentation(presentation: LocalPresentation) {
        val jsonArray = JSONArray(prefs.getString("items", "[]"))

        val jsonObject = JSONObject().apply {
            put("id", presentation.id)
            put("templatePath", presentation.templatePath)
            put("contentPath", presentation.contentPath)
            put("resultPath", presentation.resultPath)
            put("status", presentation.status)
            put("createdAt", presentation.createdAt)
        }

        jsonArray.put(jsonObject)

        prefs.edit()
            .putString("items", jsonArray.toString())
            .apply()
    }

    fun getAllPresentations(): List<LocalPresentation> {
        val jsonArray = JSONArray(prefs.getString("items", "[]"))
        val list = mutableListOf<LocalPresentation>()

        for (i in 0 until jsonArray.length()) {
            val obj = jsonArray.getJSONObject(i)

            list.add(
                LocalPresentation(
                    id = obj.getString("id"),
                    templatePath = obj.getString("templatePath"),
                    contentPath = obj.getString("contentPath"),
                    resultPath = obj.getString("resultPath"),
                    status = obj.getString("status"),
                    createdAt = obj.getLong("createdAt")
                )
            )
        }

        return list
    }

    fun getResultFile(presentation: LocalPresentation): File {
        return File(presentation.resultPath)
    }
}