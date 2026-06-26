package com.example.sildebeautifier.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun HomeScreen(
    onStartClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "Slide Beautifier")

        Text(
            text = "Make your slides more professional.",
            modifier = Modifier.padding(top = 16.dp)
        )

        Button(
            onClick = onStartClick,
            modifier = Modifier.padding(top = 24.dp)
        ) {
            Text(text = "Start Beautifying")
        }
    }
}