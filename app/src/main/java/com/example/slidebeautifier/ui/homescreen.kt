package com.example.slidebeautifier.ui


import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.slidebeautifier.ui.components.GlassBackground
import com.example.slidebeautifier.ui.components.GlassButton
import com.example.slidebeautifier.ui.components.GlassCard

@Composable
fun HomeScreen(
    onStartClick: () -> Unit
) {
    GlassBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(28.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.Start
        ) {
            Text(
                text = "Slide\nBeautifier",
                color = Color(0xFF1F2430),
                fontSize = 46.sp,
                lineHeight = 50.sp,
                fontWeight = FontWeight.Light
            )

            Spacer(modifier = Modifier.height(18.dp))

            Text(
                text = "Transform plain presentations into clean, modern, and professional slides.",
                color = Color(0xFF5F6675),
                fontSize = 16.sp,
                lineHeight = 24.sp
            )

            Spacer(modifier = Modifier.height(36.dp))

            GlassCard(
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "How it works",
                    color = Color(0xFF232735),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "Upload your original PPTX and a reference style PPTX. The system will apply the visual style to your slides.",
                    color = Color(0xFF626A78),
                    fontSize = 14.sp,
                    lineHeight = 21.sp
                )
            }

            Spacer(modifier = Modifier.height(28.dp))

            GlassButton(
                text = "Start Beautifying",
                onClick = onStartClick
            )

        }
    }
}