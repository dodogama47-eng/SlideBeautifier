package com.example.slidebeautifier.ui.components
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun GlassBackground(
    content: @Composable BoxScope.() -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFFF4F0EA),
                        Color(0xFFE8EDF7),
                        Color(0xFFF9F9FB)
                    )
                )
            )
    ) {
        Box(
            modifier = Modifier
                .size(280.dp)
                .offset(x = (-90).dp, y = 40.dp)
                .blur(85.dp)
                .background(
                    Color(0xFFB8C7FF).copy(alpha = 0.55f),
                    CircleShape
                )
        )

        Box(
            modifier = Modifier
                .size(300.dp)
                .offset(x = 170.dp, y = 390.dp)
                .blur(95.dp)
                .background(
                    Color(0xFFFFD6A5).copy(alpha = 0.52f),
                    CircleShape
                )
        )

        Box(
            modifier = Modifier
                .size(230.dp)
                .offset(x = 210.dp, y = 20.dp)
                .blur(85.dp)
                .background(
                    Color(0xFFD8C7FF).copy(alpha = 0.45f),
                    CircleShape
                )
        )

        content()
    }
}