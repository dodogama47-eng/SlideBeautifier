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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.slidebeautifier.repository.BackendRepository
import kotlinx.coroutines.launch

@Composable
fun UploadScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val backendRepository = remember { BackendRepository(context) }

    var originalFileUri by remember { mutableStateOf<Uri?>(null) }
    var styleFileUri by remember { mutableStateOf<Uri?>(null) }
    var statusText by remember { mutableStateOf("Waiting for files") }

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
                scope.launch {
                    try {
                        val result = com.example.slidebeautifier.network.BackendClient.service.healthCheck()
                        statusText = "Backend OK: ${result["message"]}"
                    } catch (e: Exception) {
                        statusText = "Backend test failed: ${e.message}"
                    }
                }
            }
        ) {
            Text("Test Backend")
        }
        Button(
            onClick = {
                originalFilePicker.launch(
                    arrayOf("application/vnd.openxmlformats-officedocument.presentationml.presentation")
                )
            },
            modifier = Modifier.padding(top = 24.dp)
        ) {
            Text(text = "Choose Content PPTX")
        }

        Text(
            text = originalFileUri?.lastPathSegment ?: "No content file selected",
            modifier = Modifier.padding(top = 8.dp)
        )

        Button(
            onClick = {
                styleFilePicker.launch(
                    arrayOf("application/vnd.openxmlformats-officedocument.presentationml.presentation")
                )
            },
            modifier = Modifier.padding(top = 24.dp)
        ) {
            Text(text = "Choose Format PPTX")
        }

        Text(
            text = styleFileUri?.lastPathSegment ?: "No format file selected",
            modifier = Modifier.padding(top = 8.dp)
        )

        Button(
            onClick = {
                val contentUri = originalFileUri
                val formatUri = styleFileUri

                if (contentUri != null && formatUri != null) {
                    scope.launch {
                        try {
                            statusText = "Uploading and generating..."

                            val response = backendRepository.uploadFiles(
                                formatUri = formatUri,
                                textUri = contentUri
                            )

                            statusText =
                                "Completed\nTask ID: ${response.task_id}\nDownload: ${response.download_url}"
                        } catch (e: Exception) {
                            statusText = "Failed: ${e.message}"
                        }
                    }
                }
            },
            enabled = originalFileUri != null && styleFileUri != null,
            modifier = Modifier.padding(top = 32.dp)
        ) {
            Text(text = "Beautify")
        }

        Text(
            text = statusText,
            modifier = Modifier.padding(top = 24.dp)
        )
    }
}