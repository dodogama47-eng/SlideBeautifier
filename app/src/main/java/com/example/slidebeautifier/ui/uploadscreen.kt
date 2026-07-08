package com.example.slidebeautifier.ui
import android.net.Uri
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
        if (uri != null) {
            statusText = "Content file selected"
        }
    }

    val styleFilePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        styleFileUri = uri
        if (uri != null) {
            statusText = "Format file selected"
        }
    }

    val statusColor = when {
        statusText.startsWith("Failed") -> Color(0xFFB42318)
        statusText.startsWith("Completed") -> Color(0xFF027A48)
        statusText.contains("OK") -> Color(0xFF175CD3)
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
                fileName = originalFileUri?.lastPathSegment ?: "No content file selected",
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
                fileName = styleFileUri?.lastPathSegment ?: "No format file selected",
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

                Spacer(modifier = Modifier.height(18.dp))

                GlassButton(
                    text = "Beautify Slides",
                    enabled = originalFileUri != null && styleFileUri != null,
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