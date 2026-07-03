package com.example.slidebeautifier.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun UploadScreen() {
    var originalFileUri by remember { mutableStateOf<Uri?>(null) }
    var styleFileUri by remember { mutableStateOf<Uri?>(null) }

    val originalFilePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        originalFileUri = uri
    }

    val styleFilePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        styleFileUri = uri
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "Upload Slides")

        Button(
            onClick = {
                originalFilePicker.launch(
                    arrayOf(
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                )
            },
            modifier = Modifier.padding(top = 24.dp)
        ) {
            Text(text = "Choose Original PPTX")
        }

        Text(
            text = originalFileUri?.lastPathSegment ?: "No original file selected",
            modifier = Modifier.padding(top = 8.dp)
        )

        Button(
            onClick = {
                styleFilePicker.launch(
                    arrayOf(
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                )
            },
            modifier = Modifier.padding(top = 24.dp)
        ) {
            Text(text = "Choose Style PPTX")
        }

        Text(
            text = styleFileUri?.lastPathSegment ?: "No style file selected",
            modifier = Modifier.padding(top = 8.dp)
        )

        Button(
            onClick = {
                //API
            },
            enabled = originalFileUri != null && styleFileUri != null,
            modifier = Modifier.padding(top = 32.dp)
        ) {
            Text(text = "Beautify")
        }
    }
}