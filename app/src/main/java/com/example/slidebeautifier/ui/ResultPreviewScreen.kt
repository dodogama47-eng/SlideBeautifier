package com.example.slidebeautifier.ui

import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.platform.LocalContext
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.slidebeautifier.model.PreviewResultData
import com.example.slidebeautifier.ui.components.GlassBackground
import com.example.slidebeautifier.ui.components.GlassButton
import com.example.slidebeautifier.ui.components.GlassCard
import com.example.slidebeautifier.repository.BackendRepository
import kotlinx.coroutines.launch

enum class PreviewMode {
    ORIGINAL,
    REFERENCE,
    BEAUTIFIED
}

@Composable
fun ResultPreviewScreen(
    previewData: PreviewResultData,
    onBackClick: () -> Unit
) {
    var currentPage by remember { mutableIntStateOf(0) }
    var previewMode by remember { mutableStateOf(PreviewMode.BEAUTIFIED) }

    val maxPageCount = listOf(
        previewData.originalPreviewImages.size,
        previewData.referencePreviewImages.size,
        previewData.beautifiedPreviewImages.size
    ).maxOrNull()?.coerceAtLeast(1) ?: 1

    val currentImageUrl = when (previewMode) {
        PreviewMode.ORIGINAL -> previewData.originalPreviewImages.getOrNull(currentPage)
        PreviewMode.REFERENCE -> previewData.referencePreviewImages.getOrNull(currentPage)
        PreviewMode.BEAUTIFIED -> previewData.beautifiedPreviewImages.getOrNull(currentPage)
    }

    val context = LocalContext.current

    val scope = rememberCoroutineScope()

    val backendRepository = remember {
        BackendRepository(context)
    }

    var downloadStatus by remember {
        mutableStateOf("")
    }

    GlassBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 42.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Preview Result",
                color = Color(0xFF202431),
                fontSize = 34.sp,
                fontWeight = FontWeight.Light
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Compare the original deck, reference style, and generated result.",
                color = Color(0xFF667085),
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
                lineHeight = 20.sp
            )

            Spacer(modifier = Modifier.height(28.dp))

            GlassCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .animateContentSize(
                        animationSpec = spring(
                            dampingRatio = 0.82f,
                            stiffness = 180f
                        )
                    )
            ) {
                Text(
                    text = "Task ID",
                    color = Color(0xFF667085),
                    fontSize = 13.sp
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = previewData.taskId,
                    color = Color(0xFF202431),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(22.dp))

                PreviewModeSelector(
                    selectedMode = previewMode,
                    onModeChange = { mode ->
                        previewMode = mode
                    }
                )

                Spacer(modifier = Modifier.height(22.dp))

                AnimatedContent(
                    targetState = currentImageUrl,
                    label = "mainPreviewImage"
                ) { imageUrl ->
                    PreviewImagePanel(
                        title = when (previewMode) {
                            PreviewMode.ORIGINAL -> "Original PPTX"
                            PreviewMode.REFERENCE -> "Reference PPTX"
                            PreviewMode.BEAUTIFIED -> "Beautified PPTX"
                        },
                        imageUrl = imageUrl
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                PageControl(
                    currentPage = currentPage,
                    pageCount = maxPageCount,
                    onPrevious = {
                        if (currentPage > 0) {
                            currentPage--
                        }
                    },
                    onNext = {
                        if (currentPage < maxPageCount - 1) {
                            currentPage++
                        }
                    }
                )
            }

            Spacer(modifier = Modifier.height(22.dp))

            GlassCard(
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "Side-by-side Comparison",
                    color = Color(0xFF202431),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(14.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    CompareMiniPreview(
                        title = "Original",
                        imageUrl = previewData.originalPreviewImages.getOrNull(currentPage),
                        modifier = Modifier.weight(1f)
                    )

                    CompareMiniPreview(
                        title = "Reference",
                        imageUrl = previewData.referencePreviewImages.getOrNull(currentPage),
                        modifier = Modifier.weight(1f)
                    )

                    CompareMiniPreview(
                        title = "Result",
                        imageUrl = previewData.beautifiedPreviewImages.getOrNull(currentPage),
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            Spacer(modifier = Modifier.height(22.dp))

            GlassCard(
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "Download",
                    color = Color(0xFF202431),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Download the generated editable PPTX file.",
                    color = Color(0xFF667085),
                    fontSize = 13.sp,
                    lineHeight = 19.sp
                )

                Spacer(modifier = Modifier.height(18.dp))

                GlassButton(
                    text = if (downloadStatus == "downloading") {
                        "Downloading..."
                    } else {
                        "Download Beautified PPTX"
                    },
                    enabled = !previewData.downloadUrl.isNullOrBlank() &&
                            downloadStatus != "downloading",
                    onClick = {
                        val downloadUrl = previewData.downloadUrl

                        if (!downloadUrl.isNullOrBlank()) {
                            scope.launch {
                                try {
                                    downloadStatus = "downloading"

                                    val savedFileName = backendRepository.downloadResult(
                                        downloadUrl = downloadUrl,
                                        taskId = previewData.taskId
                                    )

                                    downloadStatus =
                                        "Saved to Downloads/$savedFileName"
                                } catch (e: Exception) {
                                    downloadStatus =
                                        "Download failed: ${e.message}"
                                }
                            }
                        }
                    }
                )
                if (
                    downloadStatus.isNotBlank() &&
                    downloadStatus != "downloading"
                ) {
                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = downloadStatus,
                        color = if (downloadStatus.startsWith("Download failed")) {
                            Color(0xFFB42318)
                        } else {
                            Color(0xFF027A48)
                        },
                        fontSize = 13.sp,
                        lineHeight = 18.sp,
                        textAlign = TextAlign.Center
                    )
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            GlassButton(
                text = "Back to Upload",
                onClick = onBackClick
            )
        }
    }
}

@Composable
private fun PreviewModeSelector(
    selectedMode: PreviewMode,
    onModeChange: (PreviewMode) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = Color.White.copy(alpha = 0.42f),
                shape = RoundedCornerShape(22.dp)
            )
            .border(
                width = 1.dp,
                color = Color.White.copy(alpha = 0.68f),
                shape = RoundedCornerShape(22.dp)
            )
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        PreviewSegmentButton(
            text = "Original",
            selected = selectedMode == PreviewMode.ORIGINAL,
            modifier = Modifier.weight(1f),
            onClick = {
                onModeChange(PreviewMode.ORIGINAL)
            }
        )

        PreviewSegmentButton(
            text = "Reference",
            selected = selectedMode == PreviewMode.REFERENCE,
            modifier = Modifier.weight(1f),
            onClick = {
                onModeChange(PreviewMode.REFERENCE)
            }
        )

        PreviewSegmentButton(
            text = "Result",
            selected = selectedMode == PreviewMode.BEAUTIFIED,
            modifier = Modifier.weight(1f),
            onClick = {
                onModeChange(PreviewMode.BEAUTIFIED)
            }
        )
    }
}

@Composable
private fun PreviewSegmentButton(
    text: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val backgroundColor = if (selected) {
        Color.White.copy(alpha = 0.78f)
    } else {
        Color.Transparent
    }

    val textColor = if (selected) {
        Color(0xFF202431)
    } else {
        Color(0xFF667085)
    }

    Box(
        modifier = modifier
            .height(42.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(backgroundColor)
            .clickable {
                onClick()
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            color = textColor,
            fontSize = 13.sp,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal
        )
    }
}

@Composable
private fun PreviewImagePanel(
    title: String,
    imageUrl: String?
) {
    Column {
        Text(
            text = title,
            color = Color(0xFF202431),
            fontSize = 18.sp,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(modifier = Modifier.height(12.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f)
                .clip(RoundedCornerShape(24.dp))
                .background(Color.White.copy(alpha = 0.46f))
                .border(
                    width = 1.dp,
                    color = Color.White.copy(alpha = 0.70f),
                    shape = RoundedCornerShape(24.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            if (imageUrl.isNullOrBlank()) {
                PreviewPlaceholder(text = "Preview image not available yet")
            } else {
                AsyncImage(
                    model = imageUrl,
                    contentDescription = title,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
            }
        }
    }
}

@Composable
private fun PreviewPlaceholder(
    text: String
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        CircularProgressIndicator(
            color = Color(0xFF667085),
            strokeWidth = 2.dp
        )

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = text,
            color = Color(0xFF667085),
            fontSize = 13.sp,
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun PageControl(
    currentPage: Int,
    pageCount: Int,
    onPrevious: () -> Unit,
    onNext: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        SmallPageButton(
            text = "Previous",
            enabled = currentPage > 0,
            onClick = onPrevious
        )

        Spacer(modifier = Modifier.weight(1f))

        Text(
            text = "Page ${currentPage + 1} / $pageCount",
            color = Color(0xFF202431),
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(modifier = Modifier.weight(1f))

        SmallPageButton(
            text = "Next",
            enabled = currentPage < pageCount - 1,
            onClick = onNext
        )
    }
}

@Composable
private fun SmallPageButton(
    text: String,
    enabled: Boolean,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .height(42.dp)
            .width(92.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(
                if (enabled) {
                    Color.White.copy(alpha = 0.62f)
                } else {
                    Color.White.copy(alpha = 0.26f)
                }
            )
            .border(
                width = 1.dp,
                color = Color.White.copy(alpha = 0.70f),
                shape = RoundedCornerShape(18.dp)
            )
            .clickable(enabled = enabled) {
                onClick()
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            color = if (enabled) Color(0xFF202431) else Color(0xFF9CA3AF),
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun CompareMiniPreview(
    title: String,
    imageUrl: String?,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
    ) {
        Text(
            text = title,
            color = Color(0xFF667085),
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(modifier = Modifier.height(8.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(4f / 3f)
                .clip(RoundedCornerShape(16.dp))
                .background(Color.White.copy(alpha = 0.44f))
                .border(
                    width = 1.dp,
                    color = Color.White.copy(alpha = 0.64f),
                    shape = RoundedCornerShape(16.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            if (imageUrl.isNullOrBlank()) {
                Text(
                    text = "N/A",
                    color = Color(0xFF9CA3AF),
                    fontSize = 12.sp
                )
            } else {
                AsyncImage(
                    model = imageUrl,
                    contentDescription = title,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
            }
        }
    }
}