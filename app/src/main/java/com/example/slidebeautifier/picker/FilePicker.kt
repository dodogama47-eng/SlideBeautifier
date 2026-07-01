package com.example.slidebeautifier.picker

import android.content.Intent

object FilePicker {

    fun pickPptxFile(): Intent {
        return Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
    }
}