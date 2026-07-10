package com.example.slidebeautifier.ui

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.slidebeautifier.repository.BackendRepository
import com.example.slidebeautifier.ui.components.GlassBackground
import com.example.slidebeautifier.ui.components.GlassButton
import com.example.slidebeautifier.ui.components.GlassCard
import kotlinx.coroutines.launch
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
@Composable
fun UploadScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val backendRepository = remember { BackendRepository(context) }

    var originalFileUri by remember { mutableStateOf<Uri?>(null) }
    var styleFileUri by remember { mutableStateOf<Uri?>(null) }

    var originalFileName by remember { mutableStateOf("No content file selected") }
    var styleFileName by remember { mutableStateOf("No format file selected") }

    var statusText by remember { mutableStateOf("Waiting for files") }
    var isGenerating by remember { mutableStateOf(false) }
    var generationMode by remember { mutableStateOf("strict") }

    val originalFilePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        originalFileUri = uri

        if (uri != null) {
            originalFileName = getFileNameFromUri(context, uri) ?: "Selected content file"
            statusText = "Content file selected"
        }
    }

    val styleFilePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        styleFileUri = uri

        if (uri != null) {
            styleFileName = getFileNameFromUri(context, uri) ?: "Selected format file"
            statusText = "Format file selected"
        }
    }

    val statusColor = when {
        statusText.startsWith("Failed") -> Color(0xFFB42318)
        statusText.startsWith("Completed") -> Color(0xFF027A48)
        statusText.contains("OK") -> Color(0xFF175CD3)
        statusText.contains("Uploading") -> Color(0xFF175CD3)
        else -> Color(0xFF5F6675)
    }

    GlassBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 22.dp, vertical = 42.dp),
            horizontalAlignment = Alignment.Start,
            verticalArrangement = Arrangement.Top
        ) {
            Text(
                text = "Upload\nSlides",
                color = Color(0xFF202431),
                fontSize = 42.sp,
                lineHeight = 46.sp,
                fontWeight = FontWeight.Light
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Choose your content presentation and a reference format file.",
                color = Color(0xFF667085),
                fontSize = 15.sp,
                lineHeight = 22.sp
            )

            Spacer(modifier = Modifier.height(30.dp))

            GlassCard(
                modifier = Modifier
                    .fillMaxWidth(0.96f)
                    .align(Alignment.CenterHorizontally)
            ) {
                Text(
                    text = "Backend Connection",
                    color = Color(0xFF202431),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Check whether the local FastAPI backend is running.",
                    color = Color(0xFF667085),
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )

                Spacer(modifier = Modifier.height(18.dp))

                GlassButton(
                    text = "Test Backend",
                    onClick = {
                        scope.launch {
                            try {
                                val result =
                                    com.example.slidebeautifier.network.BackendClient.service.healthCheck()

                                statusText =
                                    "Backend OK: ${result["message"] ?: result["status"] ?: "connected"}"
                            } catch (e: Exception) {
                                statusText = "Backend test failed: ${e.message}"
                            }
                        }
                    }
                )
            }

            Spacer(modifier = Modifier.height(18.dp))

            FileUploadCard(
                modifier = Modifier
                    .fillMaxWidth(0.96f)
                    .align(Alignment.CenterHorizontally),
                title = "Content PPTX",
                description = "The original slide deck that contains your real content.",
                fileName = originalFileName,
                buttonText = "Choose Content PPTX",
                onClick = {
                    originalFilePicker.launch(
                        arrayOf(
                            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                        )
                    )
                }
            )

            Spacer(modifier = Modifier.height(18.dp))

            FileUploadCard(
                modifier = Modifier
                    .fillMaxWidth(0.96f)
                    .align(Alignment.CenterHorizontally),
                title = "Format PPTX",
                description = "The reference presentation used as the visual style.",
                fileName = styleFileName,
                buttonText = "Choose Format PPTX",
                onClick = {
                    styleFilePicker.launch(
                        arrayOf(
                            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                        )
                    )
                }
            )

            Spacer(modifier = Modifier.height(22.dp))

            GlassCard(
                modifier = Modifier
                    .fillMaxWidth(0.96f)
                    .align(Alignment.CenterHorizontally)
            ) {
                Text(
                    text = "Generate Result",
                    color = Color(0xFF202431),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Upload both files to the backend and generate a beautified PPTX.",
                    color = Color(0xFF667085),
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )

                Spacer(modifier = Modifier.height(16.dp))

                GenerationModeSelector(
                    selectedMode = generationMode,
                    onModeSelected = { generationMode = it }
                )

                Spacer(modifier = Modifier.height(18.dp))

                GlassButton(
                    text = if (isGenerating) "Generating..." else "Beautify Slides",
                    enabled = originalFileUri != null && styleFileUri != null && !isGenerating,
                    onClick = {
                        val contentUri = originalFileUri
                        val formatUri = styleFileUri

                        if (contentUri != null && formatUri != null) {
                            scope.launch {
                                try {
                                    isGenerating = true
                                    statusText = "Uploading and generating..."

                                    val response = backendRepository.uploadFiles(
                                        formatUri = formatUri,
                                        textUri = contentUri,
                                        generationMode = generationMode
                                    )

                                    val savedFileName = backendRepository.downloadResult(
                                        downloadUrl = response.download_url,
                                        taskId = response.task_id
                                    )

                                    statusText =
                                        "Completed\nSaved to Downloads/$savedFileName"
                                } catch (e: Exception) {
                                    statusText = "Failed: ${e.message}"
                                } finally {
                                    isGenerating = false
                                }
                            }
                        }
                    }
                )
            }

            Spacer(modifier = Modifier.height(18.dp))

            GlassCard(
                modifier = Modifier
                    .fillMaxWidth(0.96f)
                    .align(Alignment.CenterHorizontally)
            ) {
                Text(
                    text = "Status",
                    color = Color(0xFF202431),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = statusText,
                    color = statusColor,
                    fontSize = 13.sp,
                    lineHeight = 19.sp
                )
            }

            Spacer(modifier = Modifier.height(28.dp))
        }
    }
}

@Composable
fun FileUploadCard(
    modifier: Modifier = Modifier,
    title: String,
    description: String,
    fileName: String,
    buttonText: String,
    onClick: () -> Unit
) {
    GlassCard(
        modifier = modifier
    ) {
        Text(
            text = title,
            color = Color(0xFF202431),
            fontSize = 18.sp,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = description,
            color = Color(0xFF667085),
            fontSize = 13.sp,
            lineHeight = 18.sp
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = fileName,
            color = Color(0xFF3B4252),
            fontSize = 13.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )

        Spacer(modifier = Modifier.height(16.dp))

        GlassButton(
            text = buttonText,
            onClick = onClick
        )
    }
}
@Composable
fun GenerationModeSelector(
    selectedMode: String,
    onModeSelected: (String) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            text = "Generation Mode",
            color = Color(0xFF202431),
            fontSize = 15.sp,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(modifier = Modifier.height(10.dp))

        ModeCard(
            title = "Content Preserving",
            description = "Keep original wording and structure. Best for accurate or formal slides.",
            selected = selectedMode == "strict",
            onClick = { onModeSelected("strict") }
        )

        Spacer(modifier = Modifier.height(10.dp))

        ModeCard(
            title = "Design Optimized",
            description = "Allow AI to shorten, combine, and rewrite text for a better visual layout.",
            selected = selectedMode == "creative",
            onClick = { onModeSelected("creative") }
        )
    }
}


@Composable
fun ModeCard(
    title: String,
    description: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    val borderColor =
        if (selected) Color(0xFF175CD3)
        else Color(0xFFD0D5DD)

    val backgroundColor =
        if (selected) Color(0xFFEFF8FF)
        else Color.White.copy(alpha = 0.55f)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        border = BorderStroke(
            width = if (selected) 2.dp else 1.dp,
            color = borderColor
        ),
        colors = CardDefaults.cardColors(
            containerColor = backgroundColor
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            RadioButton(
                selected = selected,
                onClick = onClick
            )

            Spacer(modifier = Modifier.width(8.dp))

            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = title,
                    color = Color(0xFF202431),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = description,
                    color = Color(0xFF667085),
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }
        }
    }
}
private fun getFileNameFromUri(
    context: Context,
    uri: Uri
): String? {
    val cursor = context.contentResolver.query(
        uri,
        null,
        null,
        null,
        null
    )

    cursor?.use {
        val nameIndex = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)

        if (nameIndex >= 0 && it.moveToFirst()) {
            return it.getString(nameIndex)
        }
    }

    return null
}