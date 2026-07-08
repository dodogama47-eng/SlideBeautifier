package com.example.slidebeautifier.ui.components


import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun BusinessBackground(
    content: @Composable BoxScope.() -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFFF6F4EF),
                        Color(0xFFEAF0FA),
                        Color(0xFFF9FAFB)
                    )
                )
            )
    ) {
        Box(
            modifier = Modifier
                .size(280.dp)
                .offset(x = (-100).dp, y = 70.dp)
                .blur(90.dp)
                .background(
                    Color(0xFFB8C7FF).copy(alpha = 0.48f),
                    CircleShape
                )
        )

        Box(
            modifier = Modifier
                .size(320.dp)
                .offset(x = 160.dp, y = 420.dp)
                .blur(100.dp)
                .background(
                    Color(0xFFFFD6A5).copy(alpha = 0.45f),
                    CircleShape
                )
        )

        Box(
            modifier = Modifier
                .size(240.dp)
                .offset(x = 220.dp, y = 10.dp)
                .blur(85.dp)
                .background(
                    Color(0xFFD9C7FF).copy(alpha = 0.40f),
                    CircleShape
                )
        )

        content()
    }
}

@Composable
fun BusinessFloatingPanel(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = RoundedCornerShape(38.dp)

    Column(
        modifier = modifier
            .shadow(
                elevation = 42.dp,
                shape = shape,
                ambientColor = Color.Black.copy(alpha = 0.14f),
                spotColor = Color.Black.copy(alpha = 0.20f)
            )
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.82f),
                        Color.White.copy(alpha = 0.58f),
                        Color.White.copy(alpha = 0.42f)
                    )
                ),
                shape = shape
            )
            .border(
                border = BorderStroke(
                    width = 1.dp,
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color.White.copy(alpha = 0.96f),
                            Color.White.copy(alpha = 0.42f)
                        )
                    )
                ),
                shape = shape
            )
            .padding(26.dp),
        content = content
    )
}

@Composable
fun MotionPrimaryButton(
    text: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
    onClick: () -> Unit
) {
    val shape = RoundedCornerShape(24.dp)

    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    val scale by animateFloatAsState(
        targetValue = if (isPressed && enabled && !loading) 0.97f else 1f,
        animationSpec = spring(
            dampingRatio = 0.55f,
            stiffness = 420f
        ),
        label = "primaryButtonScale"
    )

    val elevation by animateDpAsState(
        targetValue = if (isPressed) 8.dp else 20.dp,
        animationSpec = spring(
            dampingRatio = 0.7f,
            stiffness = 360f
        ),
        label = "primaryButtonElevation"
    )

    val buttonAlpha by animateFloatAsState(
        targetValue = when {
            loading -> 0.92f
            enabled -> 1f
            else -> 0.36f
        },
        animationSpec = spring(),
        label = "primaryButtonAlpha"
    )

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(58.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .alpha(buttonAlpha)
            .shadow(
                elevation = elevation,
                shape = shape,
                ambientColor = Color(0xFF5C7CFF).copy(alpha = 0.24f),
                spotColor = Color(0xFF5C7CFF).copy(alpha = 0.34f)
            )
            .clip(shape)
            .background(
                brush = Brush.horizontalGradient(
                    colors = listOf(
                        Color(0xFF2F3545),
                        Color(0xFF4D63FF),
                        Color(0xFF6DD5FF)
                    )
                ),
                shape = shape
            )
            .clickable(
                enabled = enabled && !loading,
                interactionSource = interactionSource,
                indication = null
            ) {
                onClick()
            },
        contentAlignment = Alignment.Center
    ) {
        if (loading) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    color = Color.White,
                    strokeWidth = 2.dp
                )

                Spacer(modifier = Modifier.width(10.dp))

                Text(
                    text = "Generating...",
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        } else {
            Text(
                text = text,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
fun MotionSecondaryButton(
    text: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    onClick: () -> Unit
) {
    val shape = RoundedCornerShape(20.dp)

    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    val scale by animateFloatAsState(
        targetValue = if (isPressed && enabled) 0.96f else 1f,
        animationSpec = spring(
            dampingRatio = 0.55f,
            stiffness = 420f
        ),
        label = "secondaryButtonScale"
    )

    val backgroundAlpha by animateFloatAsState(
        targetValue = if (isPressed) 0.78f else 0.56f,
        animationSpec = spring(),
        label = "secondaryButtonAlpha"
    )

    Box(
        modifier = modifier
            .height(46.dp)
            .widthIn(min = 112.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .alpha(if (enabled) 1f else 0.4f)
            .shadow(
                elevation = if (isPressed) 2.dp else 10.dp,
                shape = shape,
                ambientColor = Color.Black.copy(alpha = 0.08f),
                spotColor = Color.Black.copy(alpha = 0.12f)
            )
            .clip(shape)
            .background(
                color = Color.White.copy(alpha = backgroundAlpha),
                shape = shape
            )
            .border(
                width = 1.dp,
                color = Color.White.copy(alpha = 0.84f),
                shape = shape
            )
            .clickable(
                enabled = enabled,
                interactionSource = interactionSource,
                indication = null
            ) {
                onClick()
            }
            .padding(horizontal = 18.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            color = Color(0xFF1F2430),
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
fun ThinDivider() {
    Spacer(modifier = Modifier.height(22.dp))

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(Color.White.copy(alpha = 0.60f))
    )

    Spacer(modifier = Modifier.height(22.dp))
}