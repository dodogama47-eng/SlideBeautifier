package com.example.slidebeautifier.ppt

import java.io.File

class LocalPptProcessor {

    fun generateResultPpt(
        templateFile: File,
        contentFile: File,
        resultFile: File
    ): File {
        templateFile.inputStream().use { input ->
            resultFile.outputStream().use { output ->
                input.copyTo(output)
            }
        }

        return resultFile
    }
}